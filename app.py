import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 기본 설정 및 데이터 보존 ---
st.set_page_config(page_title="거미줄 v29 최종", layout="wide")

if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False

# --- 2. 최상단 모드 전환 ---
st.title("💎 부석 8분할 거미줄 v29")
c1, c2 = st.columns(2)
with c1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="primary" if not st.session_state.is_real else "secondary"):
        st.session_state.is_real = False; st.rerun()
with c2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True; st.rerun()

st.divider()

# --- 3. 실전 투자 연동창 (IP 에러 해결용) ---
if st.session_state.is_real:
    with st.container(border=True):
        st.subheader("🔑 업비트 실전 연동")
        acc = st.text_input("Access Key", type="password")
        sec = st.text_input("Secret Key", type="password")
        if st.button("🔌 계좌 연결하기", use_container_width=True):
            try:
                up_real = ccxt.upbit({'apiKey': acc, 'secret': sec})
                up_real.fetch_balance()
                st.success("✅ [성공] 이제 실전 투자가 가능합니다!")
            except Exception as e:
                st.error(f"❌ 연결 실패: IP 주소({requests.get('https://api64.ipify.org').text})를 업비트에 등록했는지 확인하세요.")

# --- 4. 시세 및 자산 현황 ---
try:
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    m = st.session_state.mock_data
    
    # 알고리즘 계산 (현재가 반영)
    coin_val = (m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0
    total_a = m['yesu'] + coin_val
    s_rate = ((curr_p - m['avg']) / m['avg'] * 100) if m['avg'] > 0 else 0

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("🏦 총 자산", f"{total_a:,.0f}원")
    col_b.metric("💵 현금", f"{m['yesu']:,.0f}원")
    col_c.metric("📈 수익률", f"{s_rate:.2f}%")

    # 매수 버튼 (모의투자 전용)
    if not st.session_state.is_real:
        st.write("")
        buy_amt = 1111111 # 언니의 8분할 매수 금액
        step = len(m['logs']) + 1
        if st.button(f"🔥 {step}차 거미줄 매수 ({buy_amt:,.0f}원 투입)", use_container_width=True, type="primary"):
            if m['yesu'] >= buy_amt:
                new_inv = m['inv_p'] + buy_amt
                new_avg = curr_p if m['avg'] == 0 else new_inv / ((m['inv_p']/m['avg']) + (buy_amt/curr_p))
                m.update({"yesu": m['yesu'] - buy_amt, "inv_p": new_inv, "avg": new_avg})
                m['logs'].append({'시간': datetime.now().strftime('%H:%M:%S'), '차수': f"{step}차", '가격': f"{curr_p:,.0f}"})
                st.balloons(); st.rerun()

    # --- 5. [중요] 매매 기록 표와 차트 ---
    st.divider()
    tab1, tab2 = st.tabs(["📋 매매 기록 리스트", "📊 비트코인 차트"])
    
    with tab1:
        if m['logs']:
            st.table(pd.DataFrame(m['logs'][::-1]))
        else:
            st.info("아직 매수 기록이 없습니다. 위 버튼을 눌러보세요!")

    with tab2:
        ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe='30m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("🔄 데이터를 불러오는 중입니다... (새로고침을 눌러보세요)")

time.sleep(20); st.rerun()
