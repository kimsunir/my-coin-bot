import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. IP 및 기본 설정 ---
def get_ip():
    try: return requests.get("https://api64.ipify.org", timeout=3).text
    except: return "35.230.58.211" # 최근 확인된 IP 주소

st.set_page_config(page_title="거미줄 v25 최종", layout="wide")

# 데이터 보존용 세션 (새로고침해도 유지)
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state: st.session_state.is_real = False

# --- 2. 상단 IP 안내 (업비트에 58.211 꼭 추가하세요!) ---
my_ip = get_ip()
st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border: 2px solid #ff69b4; text-align: center;">
        <h3 style="color: white; margin: 0;">📍 현재 앱 IP: <span style="color: #ff69b4;">{my_ip}</span></h3>
        <p style="color: #cbd5e1; margin-top: 5px;">업비트에 '35.230.85.211' 외에 위 주소도 <b>쉼표(,)</b> 찍고 꼭 추가하셔야 실전이 됩니다!</p>
    </div>
""", unsafe_allow_html=True)

# --- 3. 자산 현황판 ---
st.title("💎 부석 거미줄 시스템 v25")

try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    curr_p = ticker['last']
    
    m = st.session_state.mock_data
    # 코인 가치 계산 (데이터 못 불러올 땐 산 가격 그대로 표시)
    coin_v = (m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0
    total_a = m['yesu'] + coin_v
    s_rate = ((curr_p - m['avg']) / m['avg'] * 100) if m['avg'] > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("🏦 총 자산", f"{total_a:,.0f}원")
    c2.metric("💵 보유 현금", f"{m['yesu']:,.0f}원")
    c3.metric("📈 수익률", f"{s_rate:.2f}%")

    # 매수 버튼 (모의투자 전용)
    if not st.session_state.is_real:
        st.divider()
        buy_amt = 1111111
        if st.button(f"🔥 {len(m['logs'])+1}차 매수 실행 ({buy_amt:,.0f}원 투입)", use_container_width=True, type="primary"):
            if m['yesu'] >= buy_amt:
                new_inv = m['inv_p'] + buy_amt
                new_avg = curr_p if m['avg'] == 0 else new_inv / ((m['inv_p']/m['avg']) + (buy_amt/curr_p))
                st.session_state.mock_data.update({"yesu": m['yesu'] - buy_amt, "inv_p": new_inv, "avg": new_avg})
                st.session_state.mock_data['logs'].append({'시간': datetime.now().strftime('%H:%M'), '가격': f"{curr_p:,.0f}"})
                st.balloons(); st.rerun()

    # 차트
    ohlcv = upbit.fetch_ohlcv('BTC/KRW', timeframe='30m', limit=50)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
    fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("🔄 시세 데이터를 불러오는 중입니다... 잠시만 기다려주세요!")

time.sleep(15); st.rerun()
