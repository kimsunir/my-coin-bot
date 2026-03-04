import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import os

# 1. 파일 저장 시스템 (새로고침 방어)
SAVE_FILE = "trading_data.json"

def save_data():
    data = {
        'yesu': st.session_state.yesu,
        'inv_p': st.session_state.inv_p,
        'avg': st.session_state.avg,
        'logs': st.session_state.logs,
        'history': st.session_state.history
    }
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f)

def load_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            return json.load(f)
    return None

# 2. 페이지 설정
st.set_page_config(page_title="코인 무적 엔진 v8.0", layout="wide")

# 3. 데이터 로드 및 세션 초기화
saved = load_data()
if 'yesu' not in st.session_state:
    if saved:
        st.session_state.yesu = saved.get('yesu', 10000000)
        st.session_state.inv_p = saved.get('inv_p', 0)
        st.session_state.avg = saved.get('avg', 0)
        st.session_state.logs = saved.get('logs', [])
        st.session_state.history = saved.get('history', [])
    else:
        st.session_state.yesu, st.session_state.inv_p, st.session_state.avg = 10000000, 0, 0
        st.session_state.logs, st.session_state.history = [], []

# 4. [사이드바] 설정 메뉴로 이동
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    # 키보드 방지를 위해 라디오 버튼 사용 (가로 배치)
    time_frame = st.radio(
        "차트 시간 단위", 
        ['1m', '5m', '30m', '1h', '4h', '1d', '1w'], 
        index=2,
        help="클릭하면 바로 차트가 변경됩니다."
    )
    st.divider()
    if st.button("⏹️ 전체 데이터 초기화"):
        if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
        st.session_state.clear()
        st.rerun()
    st.write("---")
    st.caption("v8.0 모바일 최적화 버전")

# 5. 실시간 데이터 가져오기 (업비트)
try:
    upbit = ccxt.upbit()
    ohlcv = upbit.fetch_ohlcv('BTC/KRW', timeframe=time_frame, limit=50)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)
    curr_price = df['close'].iloc[-1]
except:
    st.error("거래소 연결 중...")
    st.stop()

# 자산 계산
curr_v = (st.session_state.inv_p / st.session_state.avg * curr_price) if st.session_state.avg > 0 else 0
s_rate = ((curr_price - st.session_state.avg) / st.session_state.avg * 100) if st.session_state.avg > 0 else 0
total_asset = st.session_state.yesu + curr_v

# 자산 히스토리 저장
st.session_state.history.append({'time': datetime.now().strftime('%H:%M:%S'), 'total': total_asset})
if len(st.session_state.history) > 30: st.session_state.history.pop(0)

# 메인 화면 시작
st.title("💰 거미줄 자동매매")

# 6. 상단 요약 지표
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total_asset:,.0f}원")
c2.metric("💵 예수금", f"{st.session_state.yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

# 7. [코인 차트]
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='BTC')])
if st.session_state.avg > 0:
    fig.add_hline(y=st.session_state.avg, line_dash="dash", line_color="red", annotation_text="내 평단가")
fig.update_layout(height=350, margin=dict(l=5, r=5, b=5, t=5), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# 8. 매매 실행 버튼
if st.button(f"🚀 {len(st.session_state.logs)+1}차 매수 (100만원)", use_container_width=True):
    if st.session_state.yesu >= 1000000:
        if st.session_state.avg == 0:
            st.session_state.avg = curr_price
        else:
            old_q = st.session_state.inv_p / st.session_state.avg
            new_q = 1000000 / curr_price
            st.session_state.avg = (st.session_state.inv_p + 1000000) / (old_q + new_q)
        
        st.session_state.yesu -= 1000000
        st.session_state.inv_p += 1000000
        st.session_state.logs.append({
            '시간': datetime.now().strftime('%H:%M:%S'),
            '작업': f"{len(st.session_state.logs)+1}차 매수",
            '체결가': f"{curr_price:,.0f}원"
        })
        save_data()
        st.rerun()

# 9. [매매 기록 표] - 다시 부활!
if st.session_state.logs:
    st.subheader("📋 최근 매매 내역")
    log_df = pd.DataFrame(st.session_state.logs[::-1])
    st.table(log_df)

# 10. [수익 차트] - 맨 아래 작게
st.write("---")
st.caption("📉 실시간 자산 흐름")
if st.session_state.history:
    h_df = pd.DataFrame(st.session_state.history)
    fig_h = go.Figure(data=go.Scatter(x=h_df['time'], y=h_df['total'], mode='lines', line=dict(color='green')))
    fig_h.update_layout(height=200, margin=dict(l=5, r=5, b=5, t=5))
    st.plotly_chart(fig_h, use_container_width=True)

# 10초 자동 갱신
time.sleep(10)
st.rerun()
