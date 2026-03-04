import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 기본 설정 및 세션 초기화 ---
st.set_page_config(page_title="거미줄 v27 최종", layout="wide")

# 모의투자 데이터 저장소 (세션이 끊기지 않는 한 유지)
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False

# --- 2. 상단 모드 전환 ---
st.title("💎 부석 8분할 거미줄 v27")
col1, col2 = st.columns(2)
with col1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="primary" if not st.session_state.is_real else "secondary"):
        st.session_state.is_real = False
        st.rerun()
with col2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True
        st.rerun()

st.divider()

# --- 3. [실전 투자 전용] API 입력 박스 ---
# 언니! 실전 버튼 눌렀을 때 이게 안 보였던 걸 제가 고쳤어요!
if st.session_state.is_real:
    with st.container(border=True):
        st.subheader("🔑 업비트 실전 연동")
        acc_key = st.text_input("Access Key", type="password", help="업비트에서 복사한 키를 넣으세요")
        sec_key = st.text_input("Secret Key", type="password")
        if st.button("🔌 계좌 연결하기", use_container_width=True):
            try:
                upbit_real = ccxt.upbit({'apiKey': acc_key, 'secret': sec_key})
                upbit_real.fetch_balance()
                st.success("✅ 실전 계좌 연결 성공!")
            except Exception as e:
                st.error(f"❌ 연결 실패 (IP 주소를 확인하세요): {e}")

# --- 4. 시세 및 자산 현황 ---
try:
    public_api = ccxt.upbit()
    ticker = public_api.fetch_ticker('BTC/KRW')
    curr_p = ticker['last']
    
    m = st.session_state.mock_data
    # 8분할 매수 알고리즘 자산 계산
    coin_value = (m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0
    total_assets = m['yesu'] + coin_value
    profit_rate = ((curr_p - m['avg']) / m['avg'] * 100) if m['avg'] > 0 else 0

    # 자산 표시창
    a, b, c = st.columns(3)
    a.metric("🏦 총 자산", f"{total_assets:,.0f}원")
    b.metric("💵 보유 현금", f"{m['yesu']:,.0f}원")
    c.metric("📈 수익률", f"{profit_rate:.2f}%")

    # 매수 버튼 (모의투자용)
    if not st.session_state.is_real:
        st.write("")
        buy_amount = 1111111 # 언니의 8분할 투입 금액
        step = len(m['logs']) + 1
        if st.button(f"🔥 {step}차 매수 실행 ({buy_amount:,.0f}원)", use_container_width=True, type="primary"):
            if m['yesu'] >= buy_amount:
                # 알고리즘 계산: 새로운 평균단가와 보유량 업데이트
                new_inv = m['inv_p'] + buy_amount
                if m['avg'] == 0:
                    new_avg = curr_p
                else:
                    new_avg = new_inv / ((m['inv_p']/m['avg']) + (buy_amount/curr_p))
                
                # 데이터 저장
                st.session_state.mock_data.update({"yesu": m['yesu']-buy_amount, "inv_p": new_inv, "avg": new_avg})
                st.session_state.mock_data['logs'].append({
                    '시간': datetime.now().strftime('%H:%M:%S'),
                    '차수': f"{step}차",
                    '매수가': f"{curr_p:,.0f}원",
                    '투입금': f"{buy_amount:,.0f}원"
                })
                st.balloons()
                st.rerun()
            else:
                st.error("현금이 부족합니다!")

    # 매수 기록 표 (버튼 바로 아래 배치)
    if m['logs']:
        with st.expander("📋 매매 내역 확인", expanded=True):
            st.table(pd.DataFrame(m['logs'][::-1]))

    # 차트
    ohlcv = public_api.fetch_ohlcv('BTC/KRW', timeframe='30m', limit=50)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
    fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("🔄 데이터를 연결하고 있습니다...")

# --- 5. IP 주소 안내 (최하단) ---
try:
    curr_ip = requests.get("https://api64.ipify.org", timeout=3).text
    st.markdown(f"<p style='text-align:right; color:gray;'>📍 현재 IP: {curr_ip}</p>", unsafe_allow_html=True)
except: pass

time.sleep(15)
st.rerun()
