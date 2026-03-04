import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 지폴드 맞춤형 설정 및 세션 ---
st.set_page_config(page_title="부석 거미줄 v32", layout="wide")

if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False
if 'real_auth' not in st.session_state:
    st.session_state.real_auth = None

# --- 2. 사이드바 (설정창) ---
with st.sidebar:
    st.title("⚙️ 설정 및 관리")
    if st.button("🔄 전체 데이터 초기화", use_container_width=True):
        st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
        st.rerun()
    
    st.divider()
    mode = st.radio("🏠 투자 모드 선택", ["🌸 모의투자", "🚀 실전투자"])
    st.session_state.is_real = (mode == "🚀 실전투자")
    
    if st.session_state.is_real:
        st.subheader("🔑 API 연동")
        acc = st.text_input("Access Key", type="password")
        sec = st.text_input("Secret Key", type="password")
        if st.button("🔌 계좌 동기화", use_container_width=True):
            try:
                up_real = ccxt.upbit({'apiKey': acc, 'secret': sec})
                up_real.fetch_balance()
                st.session_state.real_auth = {'acc': acc, 'sec': sec}
                st.success("연결 성공!")
            except: st.error("연결 실패!")

# --- 3. 메인 엔진 (데이터 가져오기) ---
try:
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    
    if st.session_state.is_real and st.session_state.real_auth:
        up_real = ccxt.upbit({'apiKey': st.session_state.real_auth['acc'], 'secret': st.session_state.real_auth['sec']})
        bal = up_real.fetch_balance()
        r_cash = float(bal.get('KRW', {}).get('free', 0))
        r_btc_qty = float(bal.get('BTC', {}).get('total', 0))
        # 업비트 실제 평단가 가져오기
        r_avg = next((float(i['avg_buy_price']) for i in bal['info'] if i['currency'] == 'BTC'), 0)
        
        display_total = r_cash + (r_btc_qty * curr_p)
        display_cash = r_cash
        display_avg = r_avg
    else:
        m = st.session_state.mock_data
        display_total = m['yesu'] + ((m['inv_p']/m['avg']*curr_p) if m['avg']>0 else 0)
        display_cash = m['yesu']
        display_avg = m['avg']

    # 자산 현황판
    st.title("💎 부석 거미줄 v32")
    a, b, c = st.columns(3)
    a.metric("🏦 총 자산", f"{display_total:,.0f}원")
    b.metric("💵 현금 잔고", f"{display_cash:,.0f}원")
    c.metric("🎯 나의 평단", f"{display_avg:,.0f}원")

    # --- 4. 8분할 매수 주문 버튼 (실전/모의 공용) ---
    buy_amt = 1111111 # 언니의 고정 투자금
    logs = st.session_state.mock_data['logs']
    step = len(logs) + 1
    
    if st.button(f"🔥 {step}차 매수 주문 실행 ({buy_amt:,.0f}원)", use_container_width=True, type="primary"):
        if display_cash >= buy_amt:
            if st.session_state.is_real:
                # [실전 전용] 실제 시장가 매수 주문!
                up_real.create_market_buy_order('BTC/KRW', buy_amt)
                st.warning("🚀 실전 매수 주문이 체결되었습니다!")
            
            # 기록 업데이트
            new_inv = (st.session_state.mock_data['inv_p'] + buy_amt)
            new_avg = curr_p if display_avg == 0 else new_inv / ((st.session_state.mock_data['inv_p']/display_avg) + (buy_amt/curr_p))
            st.session_state.mock_data.update({"yesu": display_cash - buy_amt, "inv_p": new_inv, "avg": new_avg})
            st.session_state.mock_data['logs'].append({'시간': datetime.now().strftime('%H:%M:%S'), '차수': f"{step}차", '금액': f"{buy_amt:,.0f}"})
            st.balloons(); st.rerun()

    # --- 5. 탭 구성 ---
    st.divider()
    t1, t2 = st.tabs(["📊 코인 차트 & 평단선", "📋 매수 기록"])
    
    with t1:
        tf = st.radio("분봉 선택", ["1m", "5m", "30m", "1h", "1d"], index=2, horizontal=True)
        ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=60)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="비트코인")])
        
        # [핵심] 차트에 평단가 가로선 그리기
        if display_avg > 0:
            fig.add_hline(y=display_avg, line_dash="dash", line_color="yellow", annotation_text=f"내 평단: {display_avg:,.0f}")
            
        fig.update_layout(height=500, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        if logs: st.table(pd.DataFrame(logs[::-1]))
        else: st.info("매수 내역이 없습니다.")

except Exception as e:
    st.warning("🔄 업비트 데이터를 연결 중입니다...")

time.sleep(15); st.rerun()
