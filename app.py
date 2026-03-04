import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# 1. 화면 설정
st.set_page_config(page_title="코인 무적 엔진", layout="wide")
st.title("💰 8분할 거미줄 자동매매")

# 2. 자산 초기화
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000
if 'inv_p' not in st.session_state: st.session_state.inv_p = 0
if 'avg' not in st.session_state: st.session_state.avg = 0
if 'logs' not in st.session_state: st.session_state.logs = []

# 3. 실시간 가격 (업비트)
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
    st.success(f"✅ 연결 성공 | 현재가: {price:,.0f}원")
except:
    price = 0
    st.error("❌ 거래소 연결 대기 중...")

# 4. 수익 계산
curr_v = (st.session_state.inv_p / st.session_state.avg * price) if st.session_state.avg > 0 else 0
s_rate = ((price - st.session_state.avg) / st.session_state.avg * 100) if st.session_state.avg > 0 else 0

# 5. 대시보드 표시
st.write(f"### 🏦 총 자산: {st.session_state.yesu + curr_v:,.0f}원")
c1, c2 = st.columns(2)
c1.metric("💵 예수금", f"{st.session_state.yesu:,.0f}원")
c2.metric("📊 수익률", f"{s_rate:.2f}%")

st.divider()

# 6. 매매 버튼 로직
if st.button("🚀 1차 매수 시작 (100만원)", use_container_width=True):
    if st.session_state.yesu >= 1000000:
        st.session_state.yesu -= 1000000
        st.session_state.inv_p = 1000000
        st.session_state.avg = price
        st.session_state.logs.append([datetime.now().strftime('%H:%M'), "1차 매수", f"{price:,.0f}원"])
        st.rerun()

if st.button("⏹️ 전체 초기화", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# 7. 매매 기록
if st.session_state.logs:
    st.subheader("📅 매매 기록")
    st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '가격']))
