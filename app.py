import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="비트코인 8분할 엔진 v3.0", layout="wide")
st.title("💰 8분할 거미줄 자동매매 시스템")

# 2. 데이터 초기화 (언니의 소중한 자산 데이터)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000  # 초기 1,000만원
if 'inv_p' not in st.session_state: st.session_state.inv_p = 0      # 투자 원금
if 'avg' not in st.session_state: st.session_state.avg = 0          # 내 평단
if 'step' not in st.session_state: st.session_state.step = 0        # 현재 몇 분할인가?
if 'logs' not in st.session_state: st.session_state.logs = []        # 매매 기록

# 3. 실시간 가격 정보 (업비트)
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    price = ticker['last']
    st.success(f"✅ 업비트 실시간 연결 중 | 현재가: {price:,.0f}원")
except:
    price = 0
    st.error("❌ 거래소 연결 대기 중... 잠시 후 새로고침 해주세요.")

# 4. 수익률 및 자산 정밀 계산
# 평가 금액 = (투자원금 / 평단가) * 현재가
curr_val = (st.session_state.inv_p / st.session_state.avg * price) if st.session_state.avg > 0 else 0
s_geum = curr_val - st.session_state.inv_p # 수익금
s_rate = (s_geum / st.session_state.inv_p * 100) if st.session_state.inv_p > 0 else 0 # 수익률
total_asset = st.session_state.yesu + curr_val # 총 자산

# 5. 상단 대시보드 (언니가 한눈에 보기 편하게!)
st.subheader("📊 나의 자산 현황")
col1, col2, col3, col4 = st.columns(4)
col1.metric("🏦 총 자산", f"{total_asset:,.0f}원")
col2.metric("💵 남은 예수금", f"{st.session_state.yesu:,.0f}원")
col3.metric("📈 수익금", f"{s_geum:,.0f}원", delta=f"{s_rate:.2f}%")
col4.metric("📍 현재 단계", f"{st.session_state.step}회차 매수됨")

st.info(f"🔵 내 평단가: {st.session_state.avg:,.0f}원 | 🟠 현재가: {price:,.0f}원")

# 6. 자동 매수 로직 (언니가 요청한 8분할 옵션)
# 실행 버튼을 누르면 조건에 맞춰 작동합니다.
def buy_logic(step_name, amount):
    st.session_state.yesu -= amount
    if st.session_state.avg == 0: # 처음 살 때
        st.session_state.avg = price
    else: # 물탈 때 (평단가 재계산 공식)
        old_vol = st.session_state.inv_p / st.session_state.avg
        new_vol = amount / price
        st.session_state.avg = (st.session_state.inv_p + amount) / (old_vol + new_vol)
    
    st.session_state.inv_p += amount
    st.session_state.logs.append([datetime.now().strftime('%H:%M:%S'), step_name, f"{amount:,.0f}원", f"{price:,.0f}원"])

# 7. 제어 센터
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("🕹️ 매매 제어")
    if st.button("🚀 1차 매수 시작 (100만원)", use_container_width=True):
        if st.session_state.step == 0:
            st.session_state.step = 1
            buy_logic("1차 매수(시작)", 1000000)
            st.balloons()
            st.rerun()

    # 하락 시 자동 매수 시뮬레이션 버튼 (나중엔 자동으로 돌아가게 업그레이드 가능!)
    if st.session_state.step == 1 and s_rate <= -4:
        if st.button("⚠️ -4% 하락! 2차 물타기 실행", color="red"):
            st.session_state.step = 2
            buy_logic("2차 매수(-4%)", 1150000) # 1차의 1.15배
            st.rerun()

with c2:
    st.subheader("⚠️ 강제 종료")
    if st.button("⏹️ 모든 포지션 종료 및 초기화", use_container_width=True):
        st.session_state.yesu = 10000000
        st.session_state.inv_p = 0
        st.session_state.avg = 0
        st.session_state.step = 0
        st.session_state.logs = []
        st.warning("모든 데이터가 초기화되었습니다.")
        st.rerun()

# 8. 매매 로그 (표 형식)
st.divider()
st.subheader("📅 실시간 매매 기록")
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '종류', '금액', '체결가'])
    st.table(df)
else:
    st.write("아직 매매 기록이 없습니다.")
