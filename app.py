import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 지폴드 맞춤형 설정 ---
st.set_page_config(page_title="부석 거미줄 v33", layout="wide")

# 데이터 보존 (초기화 기능 포함)
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False
if 'real_auth' not in st.session_state:
    st.session_state.real_auth = None

# --- 2. 사이드바 (지폴드7 필수!) ---
with st.sidebar:
    st.title("⚙️ 스마트 설정")
    if st.button("🔄 모든 기록 초기화", use_container_width=True):
        st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
        st.rerun()
    
    st.divider()
    mode = st.radio("🏠 투자 모드 선택", ["🌸 모의투자", "🚀 실전투자"])
    st.session_state.is_real = (mode == "🚀 실전투자")
    
    if st.session_state.is_real:
        st.subheader("🔑 업비트 API 연동")
        acc = st.text_input("Access Key", type="password")
        sec = st.text_input("Secret Key", type="password")
        if st.button("🔌 실전 계좌 연결", use_container_width=True):
            try:
                up_test = ccxt.upbit({'apiKey': acc, 'secret': sec})
                up_test.fetch_balance()
                st.session_state.real_auth = {'acc': acc, 'sec': sec}
                st.success("✅ 실전 연결 성공!")
            except: st.error("❌ 연결 실패 (IP 확인!)")

# --- 3. 메인 데이터 엔진 ---
try:
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    
    if st.session_state.is_real and st.session_state.real_auth:
        # [실전 전용] 실제 업비트 데이터 연동
        up_real = ccxt.upbit({'apiKey': st.session_state.real_auth['acc'], 'secret': st.session_state.real_auth['sec']})
        bal = up_real.fetch_balance()
        r_cash = float(bal.get('KRW', {}).get('free', 0))
        r_btc_qty = float(bal.get('BTC', {}).get('total', 0))
        r_avg = next((float(i['avg_buy_price']) for i in bal['info'] if i['currency'] == 'BTC'), 0)
        
        display_total = r_cash + (r_btc_qty * curr_p)
        display_cash = r_cash
        display_avg = r_avg
    else:
        # [모의 전용]
        m = st.session_state.mock_data
        display_total = m['yesu'] + ((m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0)
        display_cash = m['yesu']
        display_avg = m['avg']

    # 상단 대시보드
    st.title("💎 부석 거미줄 v33")
    col1, col2, col3 = st.columns(3)
    col1.metric("🏦 총 자산", f"{display_total:,.0f}원")
    col2.metric("💵 보유 현금", f"{display_cash:,.0f}원")
    col3.metric("🎯 나의 평단", f"{display_avg:,.0f}원")

    # 매수 주문 버튼 (알고리즘 적용)
    buy_amt = 1111111 
    logs = st.session_state.mock_data['logs']
    step = len(logs) + 1
    
    if st.button(f"🔥 {step}차 매수 실행 ({buy_amt:,.0f}원 투입)", use_container_width=True, type="primary"):
        if display_cash >= buy_amt:
            if st.session_state.is_real:
                up_real.create_market_buy_order('BTC/KRW', buy_amt)
                st.toast("🚀 실전 매수 완료!")
            
            # 기록 업데이트 로직
            new_inv = (st.session_state.mock_data['inv_p'] + buy_amt)
            if display_avg == 0: new_avg = curr_p
            else: new_avg = new_inv / ((st.session_state.mock_data['inv_p']/display_avg) + (buy_amt/curr_p))
            
            st.session_state.mock_data.update({"yesu": display_cash - buy_amt, "inv_p": new_inv, "avg": new_avg})
            st.session_state.mock_data['logs'].append({
                '시간': datetime.now().strftime('%H:%M:%S'),
                '차수': f"{step}차",
                '매수가': curr_p,
                '투입금': buy_amt
            })
            st.balloons(); time.sleep(1); st.rerun()

    # --- 4. 탭 구성 (수익 차트 부활!) ---
    st.divider()
    t1, t2, t3 = st.tabs(["📊 코인 현황 & 평단선", "📈 수익 변화 차트", "📋 매매 정보표"])
    
    with t1:
        # 분봉 선택 및 차트
        tf = st.radio("분봉", ["1m", "5m", "30m", "1h", "1d"], index=2, horizontal=True)
        ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=60)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        
        fig = go.Figure(data=[go.Candlestick(
            x=pd.to_datetime(df['time'], unit='ms'),
            open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            name="BTC")])
        
        # 노란색 평단선 추가
        if display_avg > 0:
            fig.add_hline(y=display_avg, line_dash="dash", line_color="yellow", 
                          annotation_text=f"내 평단: {display_avg:,.0f}")
            
        fig.update_layout(height=450, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        # 언니가 찾으시던 수익 차트!
        if logs:
            df_logs = pd.DataFrame(logs)
            st.subheader("💰 회차별 매수 단가 흐름")
            st.line_chart(df_logs.set_index('시간')['매수가'])
            st.info("매수가 거미줄처럼 촘촘하게 깔리는지 확인하세요!")
        else:
            st.info("매수 버튼을 누르면 수익 차트가 그려집니다.")

    with t3:
        if logs:
            st.table(pd.DataFrame(logs[::-1]))
        else:
            st.info("기록이 없습니다.")

except Exception as e:
    st.warning("🔄 데이터를 불러오는 중... (API 연결 확인)")

time.sleep(20); st.rerun()
