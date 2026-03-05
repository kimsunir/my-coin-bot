import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 지폴드 최적화 및 세션 설정 ---
st.set_page_config(page_title="부석 거미줄 v38", layout="wide")

if 'm_data' not in st.session_state:
    st.session_state.m_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False
if 'r_auth' not in st.session_state:
    st.session_state.r_auth = None

# --- 2. [요청1&2] 사이드바 및 초기화 ---
with st.sidebar:
    st.title("⚙️ 거미줄 설정")
    if st.button("🔄 데이터 초기화 (모의)", use_container_width=True):
        st.session_state.m_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
        st.rerun()
    
    st.divider()
    mode = st.radio("🏠 투자 모드 선택", ["🌸 모의투자", "🚀 실전투자"])
    st.session_state.is_real = (mode == "🚀 실전투자")
    
    if st.session_state.is_real:
        st.subheader("🔑 실전 API 연동")
        acc = st.text_input("Access Key", type="password")
        sec = st.text_input("Secret Key", type="password")
        if st.button("🔌 실전 잔고 동기화", use_container_width=True):
            try:
                up_test = ccxt.upbit({'apiKey': acc, 'secret': sec})
                up_test.fetch_balance()
                st.session_state.r_auth = {'acc': acc, 'sec': sec}
                st.success("✅ 실전 연결 성공!")
            except: st.error("❌ 연결 실패 (키/IP 확인)")

# --- 3. 데이터 엔진 (요청6: 실전 자산 완벽 합산) ---
try:
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    
    if st.session_state.is_real and st.session_state.r_auth:
        up_real = ccxt.upbit({'apiKey': st.session_state.r_auth['acc'], 'secret': st.session_state.r_auth['sec']})
        bal = up_real.fetch_balance()
        r_cash = float(bal.get('KRW', {}).get('free', 0))
        r_btc_qty = float(bal.get('BTC', {}).get('total', 0))
        r_avg = next((float(i['avg_buy_price']) for i in bal['info'] if i['currency'] == 'BTC'), 0)
        
        display_total = r_cash + (r_btc_qty * curr_p)
        display_cash = r_cash
        display_avg = r_avg
    else:
        m = st.session_state.m_data
        display_total = m['yesu'] + ((m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0)
        display_cash = m['yesu']
        display_avg = m['avg']

    # 자산 현황판
    st.title("💎 부석 거미줄 시스템 v38")
    a, b, c = st.columns(3)
    a.metric("🏦 총 자산", f"{display_total:,.0f}원")
    b.metric("💵 현금 잔고", f"{display_cash:,.0f}원")
    c.metric("🎯 평단가", f"{display_avg:,.0f}원")

    # --- 4. [요청3&7] 실전 매수 버튼 및 알고리즘 ---
    buy_amt = 1111111 # 고정 투자금
    logs = st.session_state.m_data['logs']
    step = len(logs) + 1
    
    if st.button(f"🔥 {step}차 거미줄 매수 ({buy_amt:,.0f}원 투입)", use_container_width=True, type="primary"):
        if display_cash >= buy_amt:
            if st.session_state.is_real:
                # [실전 매수 기능] 진짜 업비트로 주문이 나갑니다!
                up_real.create_market_buy_order('BTC/KRW', buy_amt)
                st.warning("🚀 실전 매수 주문이 체결되었습니다!")
            
            # 기록 및 알고리즘 업데이트
            m = st.session_state.m_data
            new_inv = m['inv_p'] + buy_amt
            if m['avg'] == 0: m['avg'] = curr_p
            else: m['avg'] = new_inv / ((m['inv_p']/m['avg']) + (buy_amt/curr_p))
            m['yesu'] = display_cash - buy_amt
            m['inv_p'] = new_inv
            m['logs'].append({'시간': datetime.now().strftime('%H:%M:%S'), '차수': f"{step}차", '가격': curr_p})
            st.balloons(); time.sleep(1); st.rerun()

    # --- 5. [요청4&5] 탭 및 차트 평단선 ---
    st.divider()
    t1, t2, t3 = st.tabs(["📊 코인 현황 차트", "📈 수익 변화율", "📋 매수 정보표"])
    
    with t1:
        # 분봉 선택 (요청4: 차트 탭에 분봉 버튼 배치)
        tf = st.radio("분봉 선택", ["1m", "5m", "30m", "1h", "1d"], index=2, horizontal=True)
        ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=60)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['t'], unit='ms'), open=df['o'], high=df['h'], low=df['l'], close=df['c'])])
        
        # [요청5: 차트에 노란 평단선 추가]
        if display_avg > 0:
            fig.add_hline(y=display_avg, line_dash="dash", line_color="yellow", annotation_text=f"평단: {display_avg:,.0f}")
            
        fig.update_layout(height=450, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        if logs:
            st.subheader("💰 가격 변화 흐름")
            st.line_chart(pd.DataFrame(logs).set_index('시간')['가격'])
        else: st.info("기록이 없습니다.")

    with t3:
        if logs: st.table(pd.DataFrame(logs[::-1]))
        else: st.info("기록이 없습니다.")

except Exception as e:
    st.warning("🔄 데이터 동기화 중입니다...")

time.sleep(15); st.rerun()
