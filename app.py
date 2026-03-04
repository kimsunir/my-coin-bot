import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time

# 1. 페이지 설정
st.set_page_config(page_title="코인 무적 엔진 v6.0", layout="wide")
st.title("💰 8분할 거미줄 자동매매 시스템")

# 2. [핵심] 새로고침해도 데이터 유지 (강력 보강)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000
if 'inv_p' not in st.session_state: st.session_state.inv_p = 0
if 'avg' not in st.session_state: st.session_state.avg = 0
if 'logs' not in st.session_state: st.session_state.logs = []

# 3. 사이드바 설정 (분봉 선택)
with st.sidebar:
    st.header("⚙️ 차트 설정")
    time_frame = st.selectbox("차트 시간 (분봉)", ['1m', '5m', '15m', '30m', '1h', '1d'], index=1)
    st.write("---")
    if st.button("♻️ 데이터 강제 리셋"):
        st.session_state.clear()
        st.rerun()

# 4. 실시간 데이터 가져오기 (업비트)
try:
    upbit = ccxt.upbit()
    ohlcv = upbit.fetch_ohlcv('BTC/KRW', timeframe=time_frame, limit=60)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)
    
    curr_price = df['close'].iloc[-1]
    st.success(f"✅ 실시간 연결 중 | 현재가: {curr_price:,.0f}원")
except:
    st.error("거래소 연결 중...")
    st.stop()

# 5. 수익 계산
curr_v = (st.session_state.inv_p / st.session_state.avg * curr_price) if st.session_state.avg > 0 else 0
s_rate = ((curr_price - st.session_state.avg) / st.session_state.avg * 100) if st.session_state.avg > 0 else 0
total = st.session_state.yesu + curr_v

# 6. [차트] 비트코인 캔들 차트 + 내 평단가 선
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='비트코인')])

# 내 평단가가 있으면 차트에 가로선 긋기
if st.session_state.avg > 0:
    fig.add_hline(y=st.session_state.avg, line_dash="dash", line_color="red", annotation_text=f"내 평단: {st.session_state.avg:,.0f}")

fig.update_layout(height=400, margin=dict(l=10, r=10, b=10, t=10))
st.plotly_chart(fig, use_container_width=True)

# 7. 수익률 지표 (게이지 차트)
st.subheader("📊 자산 및 수익 현황")
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total:,.0f}원")
c2.metric("💵 예수금", f"{st.session_state.yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

# 수익률 시각화 바
st.write(f"**내 평단가 대비 진행 상황: {s_rate:.2f}%**")
st.progress(min(max((s_rate + 10) / 20, 0.0), 1.0)) # -10% ~ +10% 범위

st.divider()

# 8. 매매 버튼
buy_btn = st.button(f"🚀 {len(st.session_state.logs)+1}차 매수 실행 (100만원)", use_container_width=True)
if buy_btn:
    if st.session_state.yesu >= 1000000:
        if st.session_state.avg == 0:
            st.session_state.avg = curr_price
        else:
            old_q = st.session_state.inv_p / st.session_state.avg
            new_q = 1000000 / curr_price
            st.session_state.avg = (st.session_state.inv_p + 1000000) / (old_q + new_q)
        
        st.session_state.yesu -= 1000000
        st.session_state.inv_p += 1000000
        st.session_state.logs.append([datetime.now().strftime('%H:%M:%S'), f"{len(st.session_state.logs)}차 매수", f"{curr_price:,.0f}원"])
        st.balloons()
        st.rerun()

# 9. 매매 기록
if st.session_state.logs:
    st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '체결가']))

# 10초 자동 갱신
time.sleep(10)
st.rerun()
