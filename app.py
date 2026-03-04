import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time
import requests

# --- 1. IP 주소 가져오기 (이걸 업비트에 넣어야 함) ---
def get_ip():
    try:
        return requests.get("https://api64.ipify.org", timeout=3).text
    except:
        return "IP 확인 중... 잠시 후 새로고침하세요"

# --- 2. 페이지 설정 (사이드바 안 씀!) ---
st.set_page_config(page_title="거미줄 v19", layout="wide", initial_sidebar_state="collapsed")

if 'is_real' not in st.session_state: st.session_state.is_real = False
if 'access' not in st.session_state: st.session_state.access = ""
if 'secret' not in st.session_state: st.session_state.secret = ""

# --- 3. [최상단] 업비트 등록용 IP 주소 안내 ---
target_ip = get_ip()
st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border: 2px solid #3498db; text-align: center;">
        <p style="color: white; margin-bottom: 5px;">📍 업비트 API [IP 주소 등록] 칸에 넣을 숫자</p>
        <h2 style="color: #3498db; margin: 0;">{target_ip}</h2>
    </div>
""", unsafe_allow_html=True)

st.divider()

# --- 4. 메인 메뉴 (실전/모의 선택) ---
st.title("💰 무적 8분할 거미줄 v19")
col_m1, col_m2 = st.columns(2)
with col_m1:
    if st.button("🌸 모의투자 (핑크 테마)", use_container_width=True, type="primary" if not st.session_state.is_real else "secondary"):
        st.session_state.is_real = False; st.rerun()
with col_m2:
    if st.button("🚀 실전투자 (블루 테마)", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True; st.rerun()

# 실전 모드 시 입력창 (화면 중앙에 바로 표시)
if st.session_state.is_real:
    with st.container(border=True):
        st.subheader("🔑 실전 계좌 연동")
        st.session_state.access = st.text_input("Access Key", value=st.session_state.access, type="password")
        st.session_state.secret = st.text_input("Secret Key", value=st.session_state.secret, type="password")
        if st.button("🔌 연결 저장 및 확인", use_container_width=True):
            try:
                upbit_test = ccxt.upbit({'apiKey': st.session_state.access, 'secret': st.session_state.secret})
                upbit_test.fetch_balance()
                st.success("✅ 연결 성공!")
            except Exception as e:
                st.error(f"❌ 연결 실패 (IP 등록 확인 필요): {e}")

st.divider()

# --- 5. 차트 영역 (에러가 나도 무조건 보이게!) ---
try:
    # 차트 시간 선택 (버튼형으로 메인에 배치)
    st.write("⏱️ **차트 분봉 선택**")
    tf = st.radio("시간 단위", ['1m', '5m', '30m', '1h', '4h', '1d'], index=2, horizontal=True)

    public_upbit = ccxt.upbit()
    ohlcv = public_upbit.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)

    fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(height=400, margin=dict(l=10, r=10, b=10, t=10), template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    st.metric("현재 비트코인 가격", f"{df['close'].iloc[-1]:,.0f}원")

except Exception as e:
    st.warning("차트 데이터를 불러오는 중... (화면을 아래로 내려보세요)")

# --- 6. 매수 버튼 및 기록 ---
st.divider()
st.button("🔥 1차 거미줄 매수 실행", use_container_width=True, type="primary")

st.subheader("📋 최근 매매 내역")
st.caption("기록이 여기에 표시됩니다.")

# 자동 갱신
time.sleep(20)
st.rerun()
