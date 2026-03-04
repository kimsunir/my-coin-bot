import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 초기 설정 ---
st.set_page_config(page_title="거미줄 v26 최종", layout="wide")

if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False

# --- 2. [필수] 모드 전환 버튼 (무조건 최상단!) ---
st.title("💎 부석 거미줄 시스템 v26")
c1, c2 = st.columns(2)
with c1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="primary" if not st.session_state.is_real else "secondary"):
        st.session_state.is_real = False
        st.rerun()
with c2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True
        st.rerun()

st.divider()

# --- 3. 자산 및 시세 엔진 ---
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    curr_p = ticker['last']
    
    m = st.session_state.mock_data
    coin_v = (m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0
    total_a = m['yesu'] + coin_v
    s_rate = ((curr_p - m['avg']) / m['avg'] * 100) if m['avg'] > 0 else 0

    # 자산 현황 표시
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("🏦 총 자산", f"{total_a:,.0f}원")
    col_b.metric("💵 현금", f"{m['yesu']:,.0f}원")
    col_c.metric("📈 수익률", f"{s_rate:.2f}%")

    # 매수 버튼
    st.write("")
    buy_amt = 1111111
    btn_label = f"🔥 {len(m['logs'])+1}차 매수 실행 ({buy_amt:,.0f}원)"
    if st.button(btn_label, use_container_width=True, type="primary"):
        if m['yesu'] >= buy_amt:
            new_inv = m['inv_p'] + buy_amt
            new_avg = curr_p if m['avg'] == 0 else new_inv / ((m['inv_p']/m['avg']) + (buy_amt/curr_p))
            st.session_state.mock_data.update({"yesu": m['yesu']-buy_amt, "inv_p": new_inv, "avg": new_avg})
            st.session_state.mock_data['logs'].append({'시간': datetime.now().strftime('%H:%M'), '차수': f"{len(m['logs'])+1}차", '가격': f"{curr_p:,.0f}"})
            st.balloons()
            st.rerun()

    # 차트
    ohlcv = upbit.fetch_ohlcv('BTC/KRW', timeframe='30m', limit=50)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
    fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("🔄 데이터를 연결하고 있습니다... (새로고침을 눌러보세요)")

# --- 4. 매매 기록 표 (절대로 안 사라짐) ---
st.divider()
st.subheader("📋 매매 기록 리스트")
if st.session_state.mock_data['logs']:
    st.table(pd.DataFrame(st.session_state.mock_data['logs'][::-1]))
else:
    st.info("아직 매수 기록이 없습니다. 버튼을 눌러보세요!")

# --- 5. IP 주소 안내 (맨 아래로 배치) ---
st.write("")
try:
    my_ip = requests.get("https://api64.ipify.org", timeout=3).text
    st.caption(f"📍 현재 접속 IP: {my_ip} (업비트에 등록 확인!)")
except:
    st.caption("📍 IP 확인을 위해 새로고침이 필요합니다.")

time.sleep(20)
st.rerun()
