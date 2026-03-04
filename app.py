import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import os

# --- 1. 저장 시스템 (새로고침 방어) ---
DB_FILE = "trading_db_v12.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {"is_real": False, "access": "", "secret": "", "mock_data": {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}}

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump({
            "is_real": st.session_state.is_real,
            "access": st.session_state.access,
            "secret": st.session_state.secret,
            "mock_data": st.session_state.mock_data
        }, f)

# 세션 초기 로드
if 'db_init' not in st.session_state:
    db = load_db()
    st.session_state.update(db)
    st.session_state.db_init = True

# --- 2. 페이지 설정 및 테마 ---
st.set_page_config(page_title="코인 거미줄 v12", layout="wide")

theme_color = "#3498db" if st.session_state.is_real else "#ff69b4"
st.markdown(f"""
    <style>
    .stApp {{ border-top: 12px solid {theme_color}; }}
    .mode-tag {{ 
        background: {theme_color}; color: white; padding: 10px; 
        border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 15px;
    }}
    /* 모바일 스크롤 및 사이드바 시인성 강화 */
    section[data-testid="stSidebar"] {{ background-color: #111; width: 250px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. 사이드바 (설정 메뉴) ---
with st.sidebar:
    st.header("🛠️ 시스템 메뉴")
    st.write("화면을 위아래로 내리기 불편할 땐 이 메뉴를 활용하세요!")
    
    # 시간 단위 선택 (키보드 방지)
    tf = st.radio("⏱️ 차트 시간 선택", ['1m', '5m', '30m', '1h', '4h', '1d'], index=2)
    
    st.divider()
    if st.button("♻️ 전체 데이터 초기화", use_container_width=True):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.session_state.clear()
        st.rerun()

# --- 4. 메인 화면: 모드 전환 ---
st.markdown(f'<div class="mode-tag">{"🚀 실전 매매 운용 중" if st.session_state.is_real else "🌸 모의 투자 검증 중"}</div>', unsafe_allow_html=True)

col_m1, col_m2 = st.columns(2)
with col_m1:
    if st.button("🌸 모의투자 모드로 전환", use_container_width=True):
        st.session_state.is_real = False
        save_db()
        st.rerun()
with col_m2:
    if st.button("🚀 실전투자 모드로 전환", use_container_width=True):
        st.session_state.is_real = True
        save_db()
        st.rerun()

# 실전 모드 API 입력창
upbit = None
if st.session_state.is_real:
    with st.expander("🔑 업비트 API 키 설정", expanded=(not st.session_state.access)):
        st.session_state.access = st.text_input("Access Key", value=st.session_state.access, type="password")
        st.session_state.secret = st.text_input("Secret Key", value=st.session_state.secret, type="password")
        if st.button("💾 키 저장 및 연결"):
            save_db()
            st.rerun()
    
    if st.session_state.access and st.session_state.secret:
        try:
            upbit = ccxt.upbit({'apiKey': st.session_state.access, 'secret': st.session_state.secret, 'enableRateLimit': True})
            # 연결 확인용 가벼운 호출
            upbit.fetch_balance()
        except:
            st.error("❌ 업비트 연결 실패! 키를 확인하세요.")
            upbit = None

# --- 5. 데이터 처리 ---
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
except Exception as e:
    st.warning("🔄 데이터를 동기화 중입니다... (잠시만 기다려주세요)")
    time.sleep(2)
    st.rerun()

# --- 6. 대시보드 ---
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total_a:,.0f}원")
c2.metric("💵 예수금", f"{yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

# 차트
ohlcv = public_upbit.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
if avg_p > 0: fig.add_hline(y=avg_p, line_dash="dash", line_color="red", annotation_text="내 평단")
fig.update_layout(height=300, margin=dict(l=10, r=10, b=10, t=10), template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# --- 7. 매수 알고리즘 ---
st.divider()
logs = st.session_state.mock_data['logs']
next_step = len(logs) + 1
buy_amt = 1000000 if next_step == 1 else inv_p * (2/3)

if st.button(f"🔥 {next_step}차 거미줄 매수 ({buy_amt:,.0f}원)", use_container_width=True, type="primary"):
    if yesu >= buy_amt:
        # (모의투자 시뮬레이션 로직)
        new_inv = inv_p + buy_amt
        if avg_p == 0: new_avg = curr_price
        else:
            old_q = inv_p / avg_p
            new_q = buy_amt / curr_price
            new_avg = new_inv / (old_q + new_q)
        
        st.session_state.mock_data.update({"yesu": yesu - buy_amt, "inv_p": new_inv, "avg": new_avg})
        st.session_state.mock_data['logs'].append({'시간': datetime.now().strftime('%H:%M'), '차수': f"{next_step}차", '투입': f"{buy_amt:,.0f}"})
        save_db()
        st.balloons()
        st.rerun()

# --- 8. 매매 내역 & 자산 차트 (공존 레이아웃) ---
col_b1, col_b2 = st.columns([1, 1])
with col_b1:
    st.subheader("📋 매매 기록")
    if logs: st.table(pd.DataFrame(logs[::-1]))
    else: st.caption("기록 없음")

with col_b2:
    st.subheader("📉 수익 흐름")
    st.write("자산 흐름 차트가 로딩 중...")
    # 여기에 추후 실시간 자산 그래프 추가 예정

time.sleep(15)
st.rerun()
