import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 진짜 외부 IP 가져오기 (가장 정확한 방법) ---
def get_external_ip():
    try:
        # 여러 사이트에서 IP를 체크해서 가장 정확한 걸 가져옵니다.
        return requests.get("https://api64.ipify.org", timeout=5).text
    except:
        try: return requests.get("https://ident.me", timeout=5).text
        except: return "IP 확인 실패"

# --- 2. 기본 세션 설정 ---
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state: st.session_state.is_real = False

st.set_page_config(page_title="거미줄 v21", layout="wide")

# --- 3. [긴급] IP 등록 안내창 ---
curr_ip = get_external_ip()
st.error(f"🌐 **현재 접속 IP: {curr_ip}**")
st.info("업비트에 이미 등록한 숫자와 위 숫자가 똑같은지 확인하세요! 다르면 위 숫자를 추가로 등록해야 합니다.")

# --- 4. 메인 화면 ---
st.title("💎 부석 8분할 거미줄 v21")

col1, col2 = st.columns(2)
with col1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="primary" if not st.session_state.is_real else "secondary"):
        st.session_state.is_real = False; st.rerun()
with col2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True; st.rerun()

# 실전 연동창
if st.session_state.is_real:
    with st.expander("🔑 업비트 키 입력", expanded=True):
        acc = st.text_input("Access Key", type="password", key="acc_in")
        sec = st.text_input("Secret Key", type="password", key="sec_in")
        if st.button("🔌 계좌 연결하기"):
            try:
                upbit = ccxt.upbit({'apiKey': acc, 'secret': sec})
                upbit.fetch_balance()
                st.success("✅ 실전 계좌 연결 성공!")
            except Exception as e:
                st.error(f"❌ 연결 실패: {e}")

# --- 5. 차트 및 자산 현황 ---
try:
    upbit_p = ccxt.upbit()
    curr_p = upbit_p.fetch_ticker('BTC/KRW')['last']
    
    # 모의투자 자산 계산
    m = st.session_state.mock_data
    total_a = m['yesu'] + ( (m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0 )
    s_rate = ((curr_p - m['avg']) / m['avg'] * 100) if m['avg'] > 0 else 0

    st.subheader("📊 자산 상태")
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{total_a:,.0f}원")
    c2.metric("예수금", f"{m['yesu']:,.0f}원")
    c3.metric("수익률", f"{s_rate:.2f}%")

    # 매수 버튼 (모의투자 전용 로직 포함)
    st.divider()
    buy_amt = 1111111
    if st.button(f"
