import streamlit as st
import pandas as pd
from datetime import datetime

# 앱 설정 및 제목
st.set_page_config(page_title="비트코인 8분할 자동매매", layout="centered")

# 투자 모드 선택에 따른 배경색 변경
is_real = st.sidebar.checkbox("🚨 실제 투자 모드 (주의)")

if is_real:
    st.markdown("<style>main { background-color: #FFF0F0; }</style>", unsafe_allow_html=True)
    st.title("🔴 실제 매매 가동 중")
else:
    st.title("🟢 모의 투자 진행 중")

# 상단 수익률 차트 (예시)
st.subheader("📈 누적 수익률")
chart_data = pd.DataFrame({'Profit': [0, 1, -1, 2, 5, 4, 7]}, index=pd.date_range("2024-03-01", periods=7))
st.line_chart(chart_data)

# 8분할 매수 상태판
st.subheader("🧩 8분할 매수 단계")
cols = st.columns(4)
for i in range(8):
    with cols[i % 4]:
        st.button(f"{i+1}단계 매수", key=f"btn{i}", disabled=True)

# API 및 날짜 검색
with st.expander("🔑 API 설정 및 내역 검색"):
    st.text_input("업비트 Access Key", type="password")
    st.date_input("날짜별 기록 검색", datetime.now())

st.info("💡 팁: 실제 투자를 하려면 체크박스를 선택하세요. 화면 색이 빨갛게 바뀝니다!")
