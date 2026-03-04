import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. IP 주소 실시간 확인 ---
def get_ip():
    try: return requests.get("https://api64.ipify.org", timeout=3).text
    except: return "IP 확인 중..."

st.set_page_config(page_title="거미줄 v24", layout="wide")

# 데이터 초기화
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}

# --- 2. [가장 중요] IP 주소 안내판 ---
my_ip = get_ip()
st.error(f"🌐 **현재 앱의 진짜 IP: {my_ip}**")
st.info("업비트에 등록된 35.230.85.211와 다르죠? 위 숫자를 추가로 등록하셔야 합니다!")

st.title("💎 부석 거미줄 시스템 v24")

# 모드 전환
m1, m2 = st.columns(2)
with m1:
    if st.button("🌸 모의투자", use_container_width=True): st.session_state.is_real = False; st.rerun()
with m2:
    if st.button("🚀 실전투자", use_container_width=True): st.session_state.is_real = True; st.rerun()

# --- 3. 메인 로직 ---
try:
    upbit = ccxt.upbit()
    curr_p = upbit.fetch_ticker('BTC/KRW')['last']
    
    if st.session_state.get('is_real'):
        # 실전 모드 연결창
        acc = st.text_input("Access Key", type="password")
        sec = st.text_input("Secret Key", type="password")
        if st.button("🔌 실전 계좌 연결"):
            try:
                real_upbit = ccxt.upbit({'apiKey': acc, 'secret': sec})
                real_upbit.fetch_balance()
                st.success("✅ 연결 성공!")
            except Exception as e: st.error(f"실패: {e}")
    else:
        # 모의투자 화면
        m = st.session_state.mock_data
        total_a = m['yesu'] + ( (m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0 )
        
        st.subheader(f"💰 현재 자산: {total_a:,.0f}원")
        
        # 매수 버튼
        if st.button("🔥 모의투자 1차 매수 실행", use_container_width=True, type="primary"):
            buy_amt = 1111111
            if m['yesu'] >= buy_amt:
                new_inv = m['inv_p'] + buy_amt
                new_avg = curr_p if m['avg'] == 0 else new_inv / ((m['inv_p']/m['avg']) + (buy_amt/curr_p))
                m.update({"yesu": m['yesu'] - buy_amt, "inv_p": new_inv, "avg": new_avg})
                m['logs'].append({'시간': datetime.now().strftime('%H:%M'), '가격': f"{curr_p:,.0f}"})
                st.balloons(); st.rerun()

    # 차트
    ohlcv = upbit.fetch_ohlcv('BTC/KRW', timeframe='30m', limit=50)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
    fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(height=400, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

except: st.warning("데이터 연결 중...")

time.sleep(20); st.rerun()
