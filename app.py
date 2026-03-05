import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 지폴드 최적화 설정 ---
st.set_page_config(page_title="부석 거미줄 v34", layout="wide")

# 세션 초기화 (데이터가 없어도 에러 안 나게 방어)
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False
if 'real_auth' not in st.session_state:
    st.session_state.real_auth = None

# --- 2. 사이드바 (모든 설정은 여기서!) ---
with st.sidebar:
    st.header("⚙️ 거미줄 설정")
    mode = st.radio("🏠 투자 모드", ["🌸 모의투자", "🚀 실전투자"])
    st.session_state.is_real = (mode == "🚀 실전투자")
    
    st.divider()
    if st.session_state.is_real:
        acc = st.text_input("Access Key", type="password")
        sec = st.text_input("Secret Key", type="password")
        if st.button("🔌 실전 계좌 연결"):
            try:
                up_test = ccxt.upbit({'apiKey': acc, 'secret': sec})
                up_test.fetch_balance()
                st.session_state.real_auth = {'acc': acc, 'sec': sec}
                st.success("연결 성공!")
            except: st.error("키를 확인하세요!")
    
    if st.button("🔄 전체 초기화", use_container_width=True):
        st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
        st.rerun()

# --- 3. 메인 화면 (틀을 먼저 그립니다) ---
st.title("💎 부석 거미줄 v34")

# 기본 변수 설정
display_total, display_cash, display_avg, curr_p = 0, 0, 0, 0

try:
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    
    if st.session_state.is_real and st.session_state.real_auth:
        up_real = ccxt.upbit({'apiKey': st.session_state.real_auth['acc'], 'secret': st.session_state.real_auth['sec']})
        bal = up_real.fetch_balance()
        r_cash = float(bal.get('KRW', {}).get('free', 0))
        r_btc_qty = float(bal.get('BTC', {}).get('total', 0))
        r_avg = next((float(i['avg_buy_price']) for i in bal['info'] if i['currency'] == 'BTC'), 0)
        display_total = r_cash + (r_btc_qty * curr_p)
        display_cash, display_avg = r_cash, r_avg
    else:
        m = st.session_state.mock_data
        display_total = m['yesu'] + ((m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0)
        display_cash, display_avg = m['yesu'], m['avg']

    # 자산 지표 (무조건 표시)
    a, b, c = st.columns(3)
    a.metric("🏦 총 자산", f"{display_total:,.0f}원")
    b.metric("💵 현금", f"{display_cash:,.0f}원")
    c.metric("🎯 평단", f"{display_avg:,.0f}원")

    # 매수 버튼
    step = len(st.session_state.mock_data['logs']) + 1
    if st.button(f"🔥 {step}차 매수 (1,111,111원)", use_container_width=True, type="primary"):
        if display_cash >= 1111111:
            if st.session_state.is_real:
                up_real.create_market_buy_order('BTC/KRW', 1111111)
            
            # 데이터 업데이트
            m = st.session_state.mock_data
            new_inv = m['inv_p'] + 1111111
            m['avg'] = curr_p if m['avg']==0 else new_inv / ((m['inv_p']/m['avg']) + (1111111/curr_p))
            m['yesu'] -= 1111111
            m['inv_p'] = new_inv
            m['logs'].append({'시간': datetime.now().strftime('%H:%M:%S'), '차수': f"{step}차", '가격': curr_p})
            st.rerun()

    # --- 4. 탭 구성 (UI 뼈대) ---
    st.divider()
    t1, t2, t3 = st.tabs(["📊 코인 차트", "📈 매수 흐름", "📋 기록"])

    with t1:
        tf = st.radio("분봉", ["1m", "5m", "30m", "1h"], index=1, horizontal=True)
        ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        if display_avg > 0:
            fig.add_hline(y=display_avg, line_dash="dash", line_color="yellow")
        fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        if st.session_state.mock_data['logs']:
            st.line_chart(pd.DataFrame(st.session_state.mock_data['logs']).set_index('시간')['가격'])
        else: st.info("매수 기록이 있어야 차트가 나옵니다.")

    with t3:
        if st.session_state.mock_data['logs']:
            st.table(pd.DataFrame(st.session_state.mock_data['logs'][::-1]))
        else: st.info("기록이 없습니다.")

except Exception as e:
    st.error(f"연결 오류: {e}")

time.sleep(15); st.rerun()
