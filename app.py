import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import os

# 1. 파일 저장 시스템 (새로고침 방어용)
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
st.set_page_config(page_title="코인 무적 엔진 v7.0", layout="wide")
st.title("💰 8분할 거미줄 자동매매 시스템")

# 3. 데이터 초기화 및 로드
saved = load_data()
if 'yesu' not in st.session_state:
    if saved:
        st.session_state.yesu = saved['yesu']
        st.session_state.inv_p = saved['inv_p']
        st.session_state.avg = saved['avg']
        st.session_state.logs = saved['logs']
        st.session_state.history = saved['history']
    else:
        st.session_state.yesu = 10000000
        st.session_state.inv_p = 0
        st.session_state.avg = 0
        st.session_state.logs = []
        st.session_state.history = []

# 4. 차트 시간 선택 (콤보박스 - 상단 배치)
st.subheader("⚙️ 차트 시간 설정")
time_frame = st.selectbox(
    "보고 싶은 분봉을 선택하세요", 
    ['1m', '5m', '30m', '1h', '4h', '1d', '1w', '1y'], 
    index=1
)

# 5. 실시간 데이터 가져오기 (업비트)
try:
    upbit = ccxt.upbit()
    # 1y(1년) 같은 경우 ccxt 지원 범위에 따라 1d로 대체 처리
    tf = '1d' if time_frame in ['1w', '1y'] else time_frame
    ohlcv = upbit.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=60)
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
if len(st.session_state.history) > 50: st.session_state.history.pop(0)

# 6. [코인 현황 차트] 캔들 + 내 평단선
st.subheader(f"📈 비트코인 {time_frame} 실시간 현황")
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='BTC')])
if st.session_state.avg > 0:
    fig.add_hline(y=st.session_state.avg, line_dash="dash", line_color="red", annotation_text=f"내 평단: {st.session_state.avg:,.0f}")
fig.update_layout(height=400, margin=dict(l=10, r=10, b=10, t=10))
st.plotly_chart(fig, use_container_width=True)

# 7. 대시보드
st.subheader("📊 실시간 자산 대시보드")
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total_asset:,.0f}원")
c2.metric("💵 예수금", f"{st.session_state.yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")
st.progress(min(max((s_rate + 10) / 20, 0.0), 1.0))

st.divider()

# 8. 매매 버튼
if st.button(f"🚀 {len(st.session_state.logs)+1}차 매수 실행 (100만원 투입)", use_container_width=True):
    if st.session_state.yesu >= 1000000:
        if st.session_state.avg == 0:
            st.session_state.avg = curr_price
        else:
            old_q = st.session_state.inv_p / st.session_state.avg
            new_q = 1000000 / curr_price
            st.session_state.avg = (st.session_state.inv_p + 1000000) / (old_q + new_q)
        
        st.session_state.yesu -= 1000000
        st.session_state.inv_p += 1000000
        st.session_state.logs.append([datetime.now().strftime('%H:%M:%S'), f"{len(st.session_state.logs)+1}차 매수", f"{curr_price:,.0f}원"])
        save_data() # 데이터 즉시 저장
        st.balloons()
        st.rerun()

# 9. [수익 차트 - 맨 아래 배치]
st.write("---")
st.subheader("📉 자산 변동 추이 (수익 차트)")
if st.session_state.history:
    h_df = pd.DataFrame(st.session_state.history)
    fig_h = go.Figure(data=go.Scatter(x=h_df['time'], y=h_df['total'], mode='lines+markers', line=dict(color='green')))
    fig_h.update_layout(height=300, margin=dict(l=10, r=10, b=10, t=10))
    st.plotly_chart(fig_h, use_container_width=True)

# 초기화 버튼
if st.button("⏹️ 전체 데이터 초기화 (처음부터 시작)"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.session_state.clear()
    st.rerun()

# 10초 자동 갱신
time.sleep(10)
st.rerun()
