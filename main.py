import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# 데이터 보관 (가장 단순한 방식)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000
if 'inv' not in st.session_state: st.session_state.inv = 0
if 'avg' not in st.session_state: st.session_state.avg = 0
if 'logs' not in st.session_state: st.session_state.logs = []

st.title("💰 비트코인 8분할 엔진")

# 시세 가져오기
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
except:
    price = 0

# 계산
curr_v = (st.session_state.inv / st.session_state.avg * price) if st.session_state.avg > 0 else 0
s_geum = curr_v - st.session_state.inv
s_rate = (s_geum / st.session_state.inv * 100) if st.session_state.inv > 0 else 0
total = st.session_state.yesu + curr_v

# 화면 표시
st.metric("🏦 총 자산", f"{total:,.0f}원")
c1, c2 = st.columns(2)
c1.metric("💵 예수금", f"{st.session_state.yesu:,.0f}원")
c2.metric("📈 수익금", f"{s_geum:,.0f}원", f"{s_rate:.2f}%")

st.write(f"현재가: {price:,.0f} | 평단: {st.session_state.avg:,.0f}")

# 버튼
if st.button("▶️ 1차 매수 시작"):
    amt = 1000000
    st.session_state.yesu -= amt
    st.session_state.inv = amt
    st.session_state.avg = price
    st.session_state.logs.append([datetime.now().strftime('%H:%M'), "매수", f"{price:,.0f}"])
    st.rerun()

if st.button("⏹️ 전체 종료"):
    st.session_state.yesu = total
    st.session_state.inv, st.session_state.avg = 0, 0
    st.rerun()

st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '가격']))
