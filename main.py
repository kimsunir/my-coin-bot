import streamlit as st
import pandas as pd
import time
import ccxt
from datetime import datetime

# --- 프로그램 설정 ---
st.set_page_config(page_title="비트코인 8분할 엔진 v0.1", layout="centered")

# --- 세션 상태 초기화 (데이터 유지용) ---
if 'balance' not in st.session_state:
    st.session_state.balance = 10000000 # 모의투자 1,000만원 세팅
if 'is_running' not in st.session_state:
    st.session_state.is_running = False # 시작 버튼 상태
if 'buy_count' not in st.session_state:
    st.session_state.buy_count = 0 # 매수 단계

# --- 사이드바: 컨트롤 센터 ---
st.sidebar.header("🕹️ 컨트롤 센터")
is_real = st.sidebar.checkbox("🚨 실제 투자 모드 가동")

# --- 메인 화면 ---
if is_real:
    st.markdown("<style>main { background-color: #FFF0F0; }</style>", unsafe_allow_html=True)
    st.title("🔴 실제 투자 모드")
else:
    st.title("🟢 모의 투자 모드")

# --- 🚀 시작/정지 버튼 추가 ---
st.subheader("⚙️ 시스템 가동")
col1, col2 = st.columns(2)
with col1:
    if st.button("▶️ 자동매매 시작", use_container_width=True):
        st.session_state.is_running = True
        st.success("엔진이 가동되었습니다!")
with col2:
    if st.button("⏹️ 일시 정지", use_container_width=True):
        st.session_state.is_running = False
        st.warning("엔진이 정지되었습니다.")

# --- 실시간 시세 및 잔고 ---
st.divider()
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    current_price = ticker['last']
    
    c1, c2 = st.columns(2)
    c1.metric("현재 BTC 가격", f"{current_price:,.0f} KRW")
    c2.metric("모의 투자 잔고", f"{st.session_state.balance:,.0f} KRW")
except:
    st.error("시세를 불러오는 중...")

# --- 8분할 매수 현황판 ---
st.subheader("🧩 8분할 매수 진행도")
if st.session_state.is_running:
    st.info(f"현재 비트코인 시세를 감시하며 8분할 전략을 실행 중입니다. (현재 {st.session_state.buy_count}단계)")
else:
    st.write("가동 버튼을 누르면 8분할 매수 로직이 시작됩니다.")

cols = st.columns(4)
for i in range(8):
    with cols[i % 4]:
        if i < st.session_state.buy_count:
            st.success(f"{i+1}단계 완료")
        else:
            st.info(f"{i+1}단계 대기")

# --- 수익률 그래프 ---
st.subheader("📈 수익률 추이")
chart_data = pd.DataFrame({'Profit(%)': [0, 0.2, -0.1, 0.5, 0.8]}, index=pd.date_range("2026-03-01", periods=5))
st.line_chart(chart_data)

st.caption("v0.1: 시작 버튼 및 1,000만원 잔고 연동 완료")

# 업비트 시세 가져오기 (ccxt 사용)
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    current_price = ticker['last']
    st.metric("현재 비트코인(BTC) 가격", f"{current_price:,.0f} KRW")
except:
    st.error("시세를 불러오는 중입니다... 잠시만 기다려주세요.")
    current_price = 90000000 # 에러 시 임시 가격

# --- 8분할 매수 현황판 시각화 ---
st.write("🧩 **8분할 계단식 물타기 현황**")
cols = st.columns(4)
# 예시로 2단계까지 매수된 상황 가정
current_stage = 2 
for i in range(8):
    with cols[i % 4]:
        if i < current_stage:
            st.success(f"{i+1}단계 완료")
        else:
            st.info(f"{i+1}단계 대기")

# --- 수익률 차트 ---
chart_data = pd.DataFrame({'수익률(%)': [0, 0.5, -0.2, 1.2, 2.5]}, index=pd.date_range("2026-03-01", periods=5))
st.line_chart(chart_data)

# --- 매매 로그 검색 기능 ---
st.subheader("📅 날짜별 매매 내역")
search_date = st.date_input("조회 날짜", datetime.now())
df_logs = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '가격', '수익률'])
if df_logs.empty:
    st.write("해당 날짜에 매매 기록이 없습니다.")
else:
    st.table(df_logs)

# --- 하단 안내 ---
st.divider()
st.caption("v0.05: 실제 업비트 시세 연동 및 8분할 로직 뼈대 완성. 다음 버전에서 '자동 주문 버튼'이 활성화됩니다.")
