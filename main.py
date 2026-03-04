import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

# 1. 화면 기본 설정
st.title("🟢 비트코인 8분할 매매")

# 2. 데이터 보관함 만들기 (오류 방지용)
if 'balance' not in st.session_state:
    st.session_state.balance = 10000000
if 'logs' not in st.session_state:
    st.session_state.logs = []

# 3. 현재 자산 표시
st.metric("현재 자산", f"{st.session_state.balance:,.0f}원")

# 4. 가동 버튼
if st.button("▶️ 자동매매 시작", use_container_width=True):
    now = datetime.now().strftime('%H:%M:%S')
    st.session_state.logs.append([now, "BTC", "감시시작", "정상연동", "0%"])
    st.success("엔진 가동!")

# 5. 실시간 시세 (가장 단순하게 호출)
st.divider()
upbit = ccxt.upbit()
ticker = upbit.fetch_ticker('BTC/KRW')
price = ticker['last']
st.metric("실시간 BTC 가격", f"{price:,.0f} KRW")

# 6. 매매 내역 (복잡한 if문 없이 표시)
st.subheader("📅 최근 기록")
df = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '상태', '수익'])
st.table(df)
