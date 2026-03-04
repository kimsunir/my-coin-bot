import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# 1. 화면 설정
st.set_page_config(page_title="코인 8분할 엔진")
st.title("💰 비트코인 자동매매 (재설치 버전)")

# 2. 데이터 초기화
if 'balance' not in st.session_state:
    st.session_state.balance = 10000000
if 'logs' not in st.session_state:
    st.session_state.logs = []

# 3. 실시간 시세 (에러 방지 처리)
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
    st.success(f"현재 비트코인 시세: {price:,.0f}원")
except Exception as e:
    st.error("거래소 연결 중... 새로고침을 해주세요.")
    price = 0

# 4. 현황판
st.metric("현재 잔고", f"{st.session_state.balance:,.0f}원")

# 5. 매매 버튼
if st.button("▶️ 테스트 매수 시작", use_container_width=True):
    st.session_state.balance -= 1000000
    now = datetime.now().strftime('%H:%M:%S')
    st.session_state.logs.append([now, "BTC", "1차 매수", "성공"])
    st.balloons() # 성공 축하 효과!

# 6. 기록
if st.session_state.logs:
    st.table(pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '작업', '결과']))
