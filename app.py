import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import os

# --- 1. 저장 시스템 (절대 잊지 않는 기억력) ---
DB_FILE = "trading_db_v13.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"is_real": False, "access": "", "secret": "", "mock_data": {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}}

def save_db():
    data = {
        "is_real": st.session_state.is_real,
        "access": st.session_state.access,
        "secret": st.session_state.secret,
        "mock_data": st.session_state.mock_data
    }
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

# 세션 초기화
if 'db_init' not in st.session_state:
    db = load_db()
    for k, v in db.items(): st.session_state[k] = v
    st.session_state.db_init = True

# --- 2. 테마 설정 (핑크/블루) ---
theme_color = "#3498db" if st.session_state.is_real else "#ff69b4"
st.markdown(f"""
    <style>
    .stApp {{ border-top: 15px solid {theme_color}; background-color: #0e1117; }}
    .stButton>button {{ border-radius: 12px; height: 3em; font-weight: bold; }}
    div[data-testid="stMetricValue"] {{ color: {theme_color} !important; font-size: 1.8rem; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. 메인 상단: 모드 전환 및 설정 (사이드바 대신 메인에 배치) ---
st.title("💰 무적 8분할 거미줄 시스템")

col_m1, col_m2 = st.columns(2)
with col_m1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="secondary" if st.session_state.is_real else "primary"):
        st.session_state.is_real = False
        save_db()
        st.rerun()
with col_m2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True
        save_db()
        st.rerun()

# 실전 모드 시 API 설정창 (메인에 표시)
upbit = None
if st.session_state.is_real:
    with st.container(border=True):
        st.subheader("🔑 업비트 실전 연동")
        st.session_state.access = st.text_input("Access Key", value=st.session_state.access, type="password")
        st.session_state.secret = st.text_input("Secret Key", value=st.session_state.secret, type="password")
        if st.button("🔌 계좌 연결하기", use_container_width=True):
            save_db()
            st.rerun()
    
    if st.session_state.access and st.session_state.secret:
        try:
            upbit = ccxt.upbit({'apiKey': st.session_state.access, 'secret': st.session_state.secret, 'enableRateLimit': True})
            upbit.fetch_balance() # 연결 테스트
            st.success("✅ 업비트 실전 계좌 연결됨")
        except Exception as e:
            st.error(f"❌ 연결 실패: {e}")
            upbit = None

# --- 4. 데이터 엔진 ---
try:
    public_upbit = ccxt.upbit()
    ticker = public_upbit.fetch_ticker('BTC/KRW')
    curr_price = ticker['last']
    
    if st.session_state.is_real and upbit:
        bal = upbit.fetch_balance()
        yesu = bal['KRW']['free']
        btc = bal.get('BTC', {'total': 0, 'avgPrice': 0})
        inv_p = btc['total'] * btc['avgPrice']
        avg_p = btc['avgPrice']
    else:
        yesu = st.session_state.mock_data['yesu']
        inv_p = st.session_state.mock_data['inv_p']
        avg_p = st.session_state.mock_data['avg']

    total_a = yesu + ( (inv_p / avg_p * curr_price) if avg_p > 0 else 0 )
    s_rate = ((curr_price - avg_p) / avg_p * 100) if avg_p > 0 else 0
except:
    st.info("🔄 데이터를 불러오는 중입니다... 잠시만 기다려주세요.")
    time.sleep(2)
    st.rerun()

# --- 5. 자산 현황 ---
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total_a:,.0f}원")
c2.metric("💵 예수금", f"{yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

# --- 6. 차트 시간 설정 (메인 화면에 배치) ---
st.write("⏱️ **차트 시간 선택** (클릭하면 바로 변경)")
tf = st.segmented_control("Timeframe", ['1m', '5m', '30m', '1h', '4h', '1d'], default='30m', key="main_tf")

# 차트 그리기
ohlcv = public_upbit.fetch_ohlcv('BTC/KRW', timeframe=tf or '30m', limit=50)
df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
if avg_p > 0: fig.add_hline(y=avg_p, line_dash="dash", line_color="red", annotation_text="내 평단")
fig.update_layout(height=350, margin=dict(l=10, r=10, b=10, t=10), template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# --- 7. 매수 알고리즘 버튼 ---
st.divider()
logs = st.session_state.mock_data['logs']
next_step = len(logs) + 1
# 8분할 공식 적용: 1차는 100만(가변가능), 그 뒤로는 (지금까지 총액) * 2/3
buy_amt = 1000000 if next_step == 1 else inv_p * (2/3)

if st.button(f"🔥 {next_step}차 거미줄 매수 실행 ({buy_amt:,.0f}원 투입)", use_container_width=True, type="primary"):
    if yesu >= buy_amt:
        # (모의투자 시뮬레이션 로직)
        new_inv = inv_p + buy_amt
        if avg_p == 0: new_avg = curr_price
        else:
            old_q = inv_p / avg_p
            new_q = buy_amt / curr_price
            new_avg = new_inv / (old_q + new_q)
        
        st.session_state.mock_data.update({"yesu": yesu - buy_amt, "inv_p": new_inv, "avg": new_avg})
        st.session_state.mock_data['logs'].append({'시간': datetime.now().strftime('%H:%M'), '차수': f"{next_step}차", '투입': f"{buy_amt:,.0f}", '가격': f"{curr_price:,.0f}"})
        save_db()
        st.balloons()
        st.rerun()

# --- 8. 하단 정보
