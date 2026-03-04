import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# [핵심] 화면 충돌 방지 설정
st.set_page_config(page_title="코인 무적 엔진 v3.1", layout="wide")

# 데이터 초기화 (에러 방지용 안전 장치)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000
if 'inv_p' not in st.session_state: st.session_state.inv_p = 0
if 'avg' not in st.session_state: st.session_state.avg = 0
if 'step' not in st.session_state: st.session_state.step = 0
if 'logs' not in st.session_state: st.session_state.logs = []

st.title("💰 8분할 거미줄 자동매매")

# 실시간 시세
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
    st.success(f"✅ 연결 성공! 현재가: {price:,.0f}원")
except:
    price = 0
    st.error("❌ 거래소 연결 중...")

# 자산 계산
curr_v = (st.session_state.inv_p / st.session_state.avg * price) if st.session_state.avg > 0 else 0
s_rate = ((price - st.session_state.avg) / st.session_state.avg * 100) if st.session_state.avg > 0 else 0
total = st.session_state.yesu + curr_v

# 전광판 (에러 방지를 위해 간단한 표 형식 사용)
st.write(f"### 🏦 총 자산: {total:,.0f}원")
c1, c2 = st.columns(2)
c1.write(f"💵 예수금: {st.session_state.yesu:,.0f}원")
c2.write(f"📊 수익률: {s_rate:.2f}%")

st.divider()

# 매매 버튼
if st.session_state.step == 0:
    if st.button("🚀 1차 매수 시작 (100만원)", use_container_width=True):
        st.session_state.yesu -= 1000000
        st.session_state.inv_p = 1000000
        st.session_state.avg = price
        st.session_state.step = 1
        st.session_state.logs.append([datetime.now().strftime('%H:%M'), "1차 매수", f"{price:,.0f}"])
        st.rerun()

elif st.session_state.step >= 1:
    st.write(f"📍 현재 {st.session_state.step}차 진행 중 (평단: {st.session_state.avg:,.0f}원)")
    if st.button("⏹️ 전체 초기화", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 기록
if st.session_state.logs:
    st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '가격']))
