import streamlit as st
import pandas as pd
import ccxt

st.set_page_config(page_title="코인 엔진 v1.4")
st.title("💰 비트코인 8분할 엔진")

# 1. 시세 가져오기 (이게 되면 일단 성공!)
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
    st.success(f"✅ 서버 연결 성공! 현재가: {price:,.0f}원")
except:
    st.error("❌ 거래소 연결 대기 중...")
    price = 0

# 2. 자산 현황 (세션 데이터)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000

st.metric("💵 예수금 (잔고)", f"{st.session_state.yesu:,.0f}원")

if st.button("▶️ 1차 매수 테스트"):
    st.session_state.yesu -= 1000000
    st.balloons()
    st.rerun()
