import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 기본 설정 및 데이터 보존 ---
st.set_page_config(page_title="거미줄 v30 최종", layout="wide")

if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False
if 'real_auth' not in st.session_state:
    st.session_state.real_auth = None

# --- 2. 최상단 모드 전환 ---
st.title("💎 부석 8분할 거미줄 v30")
c1, c2 = st.columns(2)
with c1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="primary" if not st.session_state.is_real else "secondary"):
        st.session_state.is_real = False; st.rerun()
with c2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True; st.rerun()

st.divider()

# --- 3. 실전 투자 연동 및 잔고 가져오기 ---
real_cash, real_coin_val, real_total = 0, 0, 0
if st.session_state.is_real:
    with st.container(border=True):
        st.subheader("🔑 업비트 실전 연동")
        acc = st.text_input("Access Key", type="password")
        sec = st.text_input("Secret Key", type="password")
        if st.button("🔌 계좌 잔고 불러오기", use_container_width=True):
            try:
                up_real = ccxt.upbit({'apiKey': acc, 'secret': sec})
                balance = up_real.fetch_balance()
                st.session_state.real_auth = {'acc': acc, 'sec': sec}
                st.success("✅ 실전 잔고 동기화 완료!")
            except Exception as e:
                st.error("❌ 연결 실패: API 키와 IP 설정을 다시 확인하세요.")

# --- 4. 시세 및 자산 현황 (실전/모의 분기) ---
try:
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    
    if st.session_state.is_real and st.session_state.real_auth:
        # [실전] 실제 업비트 데이터 가져오기
        up_real = ccxt.upbit({'apiKey': st.session_state.real_auth['acc'], 'secret': st.session_state.real_auth['sec']})
        bal = up_real.fetch_balance()
        real_cash = float(bal.get('KRW', {}).get('free', 0))
        btc_amount = float(bal.get('BTC', {}).get('total', 0))
        real_coin_val = btc_amount * curr_p
        display_total = real_cash + real_coin_val
        display_cash = real_cash
        display_rate = 0.0 # 실전 수익률은 업비트 평단가 데이터가 필요하여 일단 0으로 표시
    else:
        # [모의] 기존 로직 유지
        m = st.session_state.mock_data
        coin_v = (m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0
        display_total = m['yesu'] + coin_v
        display_cash = m['yesu']
        display_rate = ((curr_p - m['avg']) / m['avg'] * 100) if m['avg'] > 0 else 0

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("🏦 총 자산", f"{display_total:,.0f}원")
    col_b.metric("💵 현금 잔고", f"{display_cash:,.0f}원")
    col_c.metric("📈 수익률", f"{display_rate:.2f}%")

    # 매수 버튼 (모의투자 전용)
    if not st.session_state.is_real:
        buy_amt = 1111111
        step = len(st.session_state.mock_data['logs']) + 1
        if st.button(f"🔥 {step}차 모의 매수 실행", use_container_width=True, type="primary"):
            m = st.session_state.mock_data
            if m['yesu'] >= buy_amt:
                new_inv = m['inv_p'] + buy_amt
                new_avg = curr_p if m['avg'] == 0 else new_inv / ((m['inv_p']/m['avg']) + (buy_amt/curr_p))
                m.update({"yesu": m['yesu'] - buy_amt, "inv_p": new_inv, "avg": new_avg})
                m['logs'].append({'시간': datetime.now().strftime('%H:%M:%S'), '차수': f"{step}차", '가격': f"{curr_p:,.0f}"})
                st.balloons(); st.rerun()

    # --- 5. 기록 및 차트 ---
    st.divider()
    tab1, tab2 = st.tabs(["📋 매매 기록", "📊 비트코인 차트"])
    with tab1:
        if not st.session_state.is_real:
            if st.session_state.mock_data['logs']:
                st.table(pd.DataFrame(st.session_state.mock_data['logs'][::-1]))
            else: st.info("모의투자 기록이 없습니다.")
        else:
            st.info("실전 매매 내역은 업비트 앱에서 확인 가능합니다.")
            
    with tab2:
        ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe='30m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("🔄 시세 데이터를 불러오는 중...")

time.sleep(20); st.rerun()
