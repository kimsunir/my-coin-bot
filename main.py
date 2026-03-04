import streamlit as st
import pandas as pd
import time
import ccxt # 코인 거래소 연동 라이브러리
from datetime import datetime

# --- 프로그램 설정 ---
st.set_page_config(page_title="비트코인 8분할 엔진 v0.05", layout="centered")

# --- 세션 상태 초기화 (데이터 유지용) ---
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'balance' not in st.session_state:
    st.session_state.balance = 10000000 # 모의투자 기초자산 1,000만원

# --- 사이드바: 모드 선택 및 색상 변경 ---
st.sidebar.header("🕹️ 컨트롤 센터")
is_real = st.sidebar.checkbox("🚨 실제 투자 모드 가동")

if is_real:
    st.markdown("<style>main { background-color: #FFF0F0; }</style>", unsafe_allow_html=True)
    mode_text = "🔴 실제 투자 가동 중"
else:
    mode_text = "🟢 모의 투자 시뮬레이션"

st.title(mode_text)

# --- API 키 입력창 ---
with st.expander("🔑 업비트 API 키 설정 (보안 유지)"):
    access = st.text_input("Access Key", type="password")
    secret = st.text_input("Secret Key", type="password")
    if access and secret:
        st.success("API 연결 준비 완료!")

# --- [로직] 실시간 시세 및 8분할 매매 엔진 ---
st.subheader("📊 실시간 시장 현황")

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
