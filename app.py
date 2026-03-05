import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 환경 설정 및 세션 초기화 ---
st.set_page_config(page_title="거미줄 v31 최종", layout="wide")

if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False
if 'real_auth' not in st.session_state:
    st.session_state.real_auth = None

# --- 2. 상단 모드 전환 및 새로고침 버튼 ---
st.title("💎 부석 거미줄 시스템 v31")
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="primary" if not st.session_state.is_real else "secondary"):
        st.session_state.is_real = False; st.rerun()
with c2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True; st.rerun()
with c3:
    if st.button("🔄 새로고침"): st.rerun()

st.divider()

# --- 3. [실전 투자] API 입력 및 자동 숨김 ---
if st.session_state.is_real:
    # 연결 성공하면 입력 박스를 접을 수 있게(expander) 만들었어요!
    is_connected = st.session_state.real_auth is not None
    with st.expander("🔑 업비트 API 설정 (연결 후 접어두세요)", expanded=not is_connected):
        acc = st.text_input("Access Key", type="password")
        sec = st.text_input("Secret Key", type="password")
        if st.button("🔌 계좌 잔고 불러오기", use_container_width=True):
            try:
                up_real = ccxt.upbit({'apiKey': acc, 'secret': sec})
                up_real.fetch_balance() # 연결 테스트
                st.session_state.real_auth = {'acc': acc, 'sec': sec}
                st.success("✅ 실전 계좌 동기화 완료!")
                time.sleep(1); st.rerun()
            except:
                st.error("❌ 연결 실패: API 키와 IP를 확인하세요.")

# --- 4. 데이터 엔진 (실전 자산 합산 로직) ---
try:
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    
    if st.session_state.is_real and st.session_state.real_auth:
        up_real = ccxt.upbit({'apiKey': st.session_state.real_auth['acc'], 'secret': st.session_state.real_auth['sec']})
        bal = up_real.fetch_balance()
        # 현금 + 코인 가치 합산 (언니가 말씀하신 총자산 불일치 해결!)
        r_cash = float(bal.get('KRW', {}).get('free', 0))
        r_btc_qty = float(bal.get('BTC', {}).get('total', 0))
        r_btc_val = r_btc_qty * curr_p
        
        display_total = r_cash + r_btc_val
        display_cash = r_cash
        # 업비트 제공 평단가 가져오기
        r_avg = next((float(i['avg_buy_price']) for i in bal['info'] if i['currency'] == 'BTC'), 0)
        display_rate = ((curr_p - r_avg) / r_avg * 100) if r_avg > 0 else 0
    else:
        m = st.session_state.mock_data
        coin_v = (m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0
        display_total = m['yesu'] + coin_v
        display_cash = m['yesu']
        display_rate = ((curr_p - m['avg']) / m['avg'] * 100) if m['avg'] > 0 else 0

    # 자산 현황판
    a, b, c = st.columns(3)
    a.metric("🏦 총 자산 (현금+코인)", f"{display_total:,.0f}원")
    b.metric("💵 현금 잔고", f"{display_cash:,.0f}원")
    c.metric("📈 수익률", f"{display_rate:.2f}%")

    # 매수 버튼
    if not st.session_state.is_real:
        buy_amt = 1111111
        step = len(st.session_state.mock_data['logs']) + 1
        if st.button(f"🔥 {step}차 매수 실행 ({buy_amt:,.0f}원 투입)", use_container_width=True, type="primary"):
            m = st.session_state.mock_data
            if m['yesu'] >= buy_amt:
                new_inv = m['inv_p'] + buy_amt
                new_avg = curr_p if m['avg'] == 0 else new_inv / ((m['inv_p']/m['avg']) + (buy_amt/curr_p))
                m.update({"yesu": m['yesu'] - buy_amt, "inv_p": new_inv, "avg": new_avg})
                m['logs'].append({'시간': datetime.now().strftime('%H:%M:%S'), '차수': f"{step}차", '매수가': f"{curr_p:,.0f}", '투입금': f"{buy_amt:,.0f}"})
                st.rerun()

    # --- 5. 탭 구성 (매수기록, 수익차트, 비트차트) ---
    st.divider()
    t1, t2, t3 = st.tabs(["📋 매수 정보표", "📈 수익 변화율", "📊 비트코인 차트"])
    
    with t1:
        if not st.session_state.is_real:
            if st.session_state.mock_data['logs']:
                st.table(pd.DataFrame(st.session_state.mock_data['logs'][::-1]))
            else: st.info("기록이 없습니다.")
        else: st.info("실전 매매는 업비트 앱에서 확인!")

    with t2:
        # 수익 차트 (간이 시뮬레이션)
        if not st.session_state.is_real and st.session_state.mock_data['logs']:
            df_rev = pd.DataFrame(st.session_state.mock_data['logs'])
            st.line_chart(df_rev.set_index('시간')['매수가'])
        else: st.info("수익 차트를 그리기에 데이터가 부족합니다.")

    with t3:
        # 분봉 선택 버튼 추가!
        tf = st.radio("분봉 선택", ["1m", "5m", "30m", "1h", "1d"], index=2, horizontal=True)
        ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning("🔄 데이터 연결 중... 잠시만 기다려주세요.")

time.sleep(20); st.rerun()
