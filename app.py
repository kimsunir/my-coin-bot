import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# 1. 기본 설정 (언니의 전용 화면)
st.set_page_config(page_title="코인 8분할 무적 엔진", layout="wide")
st.title("💰 8분할 거미줄 자동매매 시스템 v3.0")

# 2. 데이터 초기화 (언니의 1,000만원 자산 설정)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000
if 'inv_p' not in st.session_state: st.session_state.inv_p = 0
if 'avg' not in st.session_state: st.session_state.avg = 0
if 'step' not in st.session_state: st.session_state.step = 0
if 'logs' not in st.session_state: st.session_state.logs = []

# 3. 실시간 가격 (업비트)
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
    st.success(f"✅ 실시간 연결 성공 | 현재가: {price:,.0f}원")
except:
    price = 0
    st.error("❌ 거래소 연결 대기 중...")

# 4. 수익 및 자산 정밀 계산
curr_val = (st.session_state.inv_p / st.session_state.avg * price) if st.session_state.avg > 0 else 0
s_geum = curr_val - st.session_state.inv_p
s_rate = (s_geum / st.session_state.inv_p * 100) if st.session_state.inv_p > 0 else 0
total_asset = st.session_state.yesu + curr_val

# 5. 상단 대시보드 (수익률 전광판)
st.subheader("📊 실시간 자산 현황")
c1, c2, c3, c4 = st.columns(4)
c1.metric("🏦 총 자산", f"{total_asset:,.0f}원")
c2.metric("💵 남은 예수금", f"{st.session_state.yesu:,.0f}원")
c3.metric("📈 수익금", f"{s_geum:,.0f}원")
c4.metric("📊 수익률", f"{s_rate:.2f}%")

st.info(f"📍 내 평단: {st.session_state.avg:,.0f}원 | 🟠 현재가: {price:,.0f}원 | 🚀 진행 단계: {st.session_state.step}/8분할")

# 6. 매매 함수 (수량까지 정밀하게 계산)
def buy_coin(name, amt):
    if st.session_state.avg == 0:
        st.session_state.avg = price
    else:
        old_qty = st.session_state.inv_p / st.session_state.avg
        new_qty = amt / price
        st.session_state.avg = (st.session_state.inv_p + amt) / (old_qty + new_qty)
    st.session_state.yesu -= amt
    st.session_state.inv_p += amt
    st.session_state.logs.append([datetime.now().strftime('%H:%M:%S'), name, f"{amt:,.0f}원", f"{price:,.0f}원"])

# 7. 8분할 거미줄 로직 제어판
st.divider()
col_btn, col_info = st.columns([2, 1])

with col_btn:
    st.subheader("🕹️ 단계별 매매 실행")
    
    # 1차 매수 (시작)
    if st.session_state.step == 0:
        if st.button("🚀 1차 매수 시작 (100만원)", use_container_width=True):
            st.session_state.step = 1
            buy_coin("1차 시작", 1000000)
            st.balloons()
            st.rerun()

    # 2차 매수 (-4% 하락 시 1차의 1.15배)
    elif st.session_state.step == 1:
        st.warning(f"현재 수익률 {s_rate:.2f}% | -4% 도달 시 2차 매수 버튼이 활성화됩니다.")
        if s_rate <= -4 or st.checkbox("강제 2차 매수"):
            if st.button("⚠️ 2차 물타기 실행 (115만원)", use_container_width=True):
                st.session_state.step = 2
                buy_coin("2차(-4%)", 1150000)
                st.rerun()

    # 3차 매수 (-6% 하락 시 전체의 2/3)
    elif st.session_state.step == 2:
        st.error(f"현재 수익률 {s_rate:.2f}% | -6% 도달 시 3차 매수 버튼 활성화")
        if s_rate <= -6 or st.checkbox("강제 3차 매수"):
            buy_amt = st.session_state.inv_p * (2/3)
            if st.button(f"🚨 3차 물타기 실행 ({buy_amt:,.0f}원)", use_container_width=True):
                st.session_state.step = 3
                buy_coin("3차(-6%)", buy_amt)
                st.rerun()

with col_info:
    st.subheader("⚙️ 설정")
    if st.button("⏹️ 전체 종료 및 초기화", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 8. 매매 로그
st.divider()
st.subheader("📅 실시간 매매 기록")
if st.session_state.logs:
    st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '투입금액', '체결가']))
