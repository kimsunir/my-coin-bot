import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# [필수] 에러 방지용 설정
st.set_page_config(page_title="코인 무적 엔진 v3.2", layout="wide")

# 데이터 초기화 (세션 보관)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000
if 'inv_p' not in st.session_state: st.session_state.inv_p = 0
if 'avg' not in st.session_state: st.session_state.avg = 0
if 'logs' not in st.session_state: st.session_state.logs = []

st.title("💰 8분할 거미줄 자동매매")

# 업비트 시세 가져오기
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
    st.success(f"✅ 업비트 연결 성공! 현재가: {price:,.0f}원")
except Exception as e:
    price = 0
    st.error("🔄 거래소 데이터를 읽어오는 중입니다...")

# 자산 및 수익률 계산
curr_val = (st.session_state.inv_p / st.session_state.avg * price) if st.session_state.avg > 0 else 0
s_rate = ((price - st.session_state.avg) / st.session_state.avg * 100) if st.session_state.avg > 0 else 0
total = st.session_state.yesu + curr_val

# 대시보드 (에러에 강한 단순 텍스트 방식)
st.subheader("📊 실시간 자산 현황")
st.write(f"### 🏦 총 자산: **{total:,.0f}원**")
st.write(f"💵 예수금: {st.session_state.yesu:,.0f}원 | 📈 수익률: {s_rate:.2f}%")

st.divider()

# 매매 버튼
if st.button("🚀 1차 매수 시작 (100만원)", use_container_width=True):
    if st.session_state.yesu >= 1000000:
        st.session_state.yesu -= 1000000
        st.session_state.inv_p = 1000000
        st.session_state.avg = price
        st.session_state.logs.append([datetime.now().strftime('%H:%M:%S'), "1차 매수", f"{price:,.0f}원"])
        st.balloons()
        st.rerun()

if st.button("⏹️ 전체 초기화", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# 매매 기록
if st.session_state.logs:
    st.subheader("📅 매매 기록")
    st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '체결가']))
