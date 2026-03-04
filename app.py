import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# 1. 화면 기본 설정
st.set_page_config(page_title="코인 엔진 v1.3", layout="wide")
st.title("💰 비트코인 8분할 엔진")

# 2. 데이터 초기화 (세션 스테이트 사용)
if 'yesu' not in st.session_state:
    st.session_state.yesu = 10000000
if 'inv' not in st.session_state:
    st.session_state.inv = 0
if 'avg' not in st.session_state:
    st.session_state.avg = 0
if 'logs' not in st.session_state:
    st.session_state.logs = []

# 3. 실시간 가격 가져오기
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
except:
    price = 0

# 4. 수익 및 자산 계산
curr_val = (st.session_state.inv / st.session_state.avg * price) if st.session_state.avg > 0 else 0
s_geum = curr_val - st.session_state.inv
s_rate = (s_geum / st.session_state.inv * 100) if st.session_state.inv > 0 else 0
total = st.session_state.yesu + curr_val

# 5. 전광판 표시
st.metric("🏦 총 자산", f"{total:,.0f}원")
c1, c2, c3 = st.columns(3)
c1.metric("💵 예수금 (잔고)", f"{st.session_state.yesu:,.0f}원")
c2.metric("📈 수익금", f"{s_geum:,.0f}원")
c3.metric("📊 수익률", f"{s_rate:.2f}%")

st.divider()
st.info(f"📍 현재가: {price:,.0f}원 | 🔵 내 평단: {st.session_state.avg:,.0f}원")

# 6. 매매 버튼
col1, col2 = st.columns(2)
if col1.button("▶️ 1차 매수 시작", use_container_width=True):
    amt = 1000000
    st.session_state.yesu -= amt
    st.session_state.inv = amt
    st.session_state.avg = price
    st.session_state.logs.append([datetime.now().strftime('%H:%M'), "1차 매수", f"{price:,.0f}"])
    st.rerun()

if col2.button("⏹️ 전체 종료", use_container_width=True):
    st.session_state.yesu = total
    st.session_state.inv, st.session_state.avg = 0, 0
    st.session_state.logs = []
    st.rerun()

# 7. 기록 표
if st.session_state.logs:
    st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '가격']))
