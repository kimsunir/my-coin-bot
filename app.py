import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime


st.set_page_config(page_title="거미줄 v39", layout="wide")

if 'm' not in st.session_state:
    st.session_state.m = {"y": 10000000, "inv": 0, "avg": 0, "logs": []}
if 'real' not in st.session_state:
    st.session_state.real = False


with st.sidebar:
    st.header("⚙️ 설정")
    st.session_state.real = st.checkbox("🚀 실전모드 작동")
    if st.button("🔄 전체 초기화"):
        st.session_state.m = {"y": 10000000, "inv": 0, "avg": 0, "logs": []}
        st.rerun()
    st.divider()
    acc = st.text_input("Access Key", type="password")
    sec = st.text_input("Secret Key", type="password")


try:
    up = ccxt.upbit()
    curr_p = up.fetch_ticker('BTC/KRW')['last']

    if st.session_state.real and acc and sec:
        try:
            r_up = ccxt.upbit({'apiKey': acc, 'secret': sec})
            bal = r_up.fetch_balance()
            cash = float(bal'KRW')
            btc_val = float(bal'BTC') * curr_p
            avg_p = next((float(i['avg_buy_price']) for i in bal['info'] if i['currency'] == 'BTC'), 0)
            total = cash + btc_val
        except: cash, avg_p, total = 0, 0, 0
    else:
        m = st.session_state.m
        cash, avg_p = m['y'], m['avg']
        total = cash + ((m['inv']/avg_p*curr_p) if avg_p > 0 else 0)


    st.title("💎 부석 거미줄 v39")
    a, b, c = st.columns(3)
    a.metric("🏦 총자산", f"{total:,.0f}")
    b.metric("💵 현금", f"{cash:,.0f}")
    c.metric("🎯 평단", f"{avg_p:,.0f}")


    step = len(st.session_state.m['logs']) + 1
    if st.button(f"🔥 {step}차 매수 실행 (1,111,111원)", use_container_width=True, type="primary"):
        if cash >= 1111111:
            if st.session_state.real: # 실제 주문
                r_up.create_market_buy_order('BTC/KRW', 1111111)

            m = st.session_state.m
            new_inv = m['inv'] + 1111111
            m['avg'] = curr_p if m['avg']==0 else new_inv / ((m['inv']/m['avg']) + (1111111/curr_p))
            m['y'] = cash - 1111111
            m['inv'] = new_inv
            m['logs'].append({'시간': datetime.now().strftime('%H:%M'), '가격': curr_p})
            st.rerun()


    t1, t2 = st.tabs(["📊 차트 & 평단선", "📋 매수 기록"])
    with t1:
        tf = st.radio("분봉", ["1m", "5m", "30m", "1h"], index=2, horizontal=True)
        ohlcv = up.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['t'], unit='ms'), open=df['o'], high=df['h'], low=df['l'], close=df['c'])])
        if avg_p > 0: # 노란 평단선!
            fig.add_hline(y=avg_p, line_dash="dash", line_color="yellow")
        fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)
    with t2:
        if st.session_state.m

except Exception as e:
    st.warning("📡 연결 중...")
