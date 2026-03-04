import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import os
import requests

# --- 1. 내 서버 IP 확인 (실패해도 멈추지 않게 설정) ---
def get_ip():
    try:
        return requests.get("https://api64.ipify.org", timeout=5).text
    except:
        return "IP 확인 중... (새로고침 해주세요)"

# --- 2. 데이터 저장/로드 (새로고침 방어) ---
DB_FILE = "trading_db_v17.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"is_real": False, "access": "", "secret": "", "mock_data": {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}}

def save_db():
    data = {"is_real": st.session_state.is_real, "access": st.session_state.access, "secret": st.session_state.secret, "mock_data": st.session_state.mock_data}
    with open(DB_FILE, 'w') as f: json.dump(data, f)

if 'db_init' not in st.session_state:
    db = load_db()
    for k, v in db.items(): st.session_state[k] = v
    st.session_state.db_init = True

# --- 3. 테마 및 디자인 ---
theme_color = "#3498db" if st.session_state.is_real else "#ff69b4"
st.set_page_config(page_title="거미줄 v17", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ border-top: 15px solid {theme_color}; background-color: #0e1117; }}
    .ip-banner {{
        background: #1e293b; color: white; padding: 15px; border-radius: 10px;
        text-align: center; border: 2px solid {theme_color}; margin-bottom: 20px;
    }}
    .metric-card {{ background: #161b22; padding: 10px; border-radius: 10px; text-align: center; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. 🌐 [가장 중요] 업비트 등록용 IP 주소 ---
my_server_ip = get_ip()
st.markdown(f"""
    <div class="ip-banner">
        <p style="margin:0; font-size:0.9rem;">📍 업비트 API [특정 IP 등록] 칸에 아래 숫자를 넣으세요</p>
        <p style="margin:5px 0; font-size:1.5rem; font-weight:bold; color:{theme_color};">{my_server_ip}</p>
    </div>
""", unsafe_allow_html=True)

# --- 5. 모드 전환 및 설정 ---
st.title("💎 무적 8분할 거미줄 v17")
m1, m2 = st.columns(2)
with m1:
    if st.button("🌸 모의투자 (핑크)", use_container_width=True, type="primary" if not st.session_state.is_real else "secondary"):
        st.session_state.is_real = False; save_db(); st.rerun()
with m2:
    if st.button("🚀 실전투자 (블루)", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True; save_db(); st.rerun()

# 실전 연동창 (실전 모드일 때만 표시)
upbit = None
if st.session_state.is_real:
    with st.expander("🔑 업비트 키 입력 및 연결", expanded=True):
        st.session_state.access = st.text_input("Access Key", value=st.session_state.access, type="password")
        st.session_state.secret = st.text_input("Secret Key", value=st.session_state.secret, type="password")
        if st.button("💾 연결 저장하기", use_container_width=True):
            save_db(); st.rerun()
    
    if st.session_state.access and st.session_state.secret:
        try:
            upbit = ccxt.upbit({'apiKey': st.session_state.access, 'secret': st.session_state.secret})
            upbit.fetch_balance()
            st.success("✅ 실전 계좌 연결 성공!")
        except Exception as e:
            st.error(f"❌ 연결 대기 중: {e}")

# --- 6. 데이터 로직 (에러 나도 차트는 보이게!) ---
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
        yesu, inv_p, avg_p = st.session_state.mock_data['yesu'], st.session_state.mock_data['inv_p'], st.session_state.mock_data['avg']

    total_a = yesu + ( (inv_p / avg_p * curr_price) if avg_p > 0 else 0 )
    s_rate = ((curr_price - avg_p) / avg_p * 100) if avg_p > 0 else 0
except:
    st.warning("🔄 데이터 연결 중... 잠시만 기다려주세요.")
    time.sleep(2); st.rerun()

# --- 7. 대시보드 및 차트 ---
st.subheader("📊 나의 자산 현황")
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total_a:,.0f}원")
c2.metric("💵 예수금", f"{yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

st.divider()

# 차트 시간 선택 버튼
tf = st.radio("⏱️ 차트 시간", ['1m', '5m', '30m', '1h', '4h', '1d'], index=2, horizontal=True)

# 캔들 차트
ohlcv = public_upbit.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
if avg_p > 0: fig.add_hline(y=avg_p, line_dash="dash", line_color="red", annotation_text="내 평단")
fig.update_layout(height=400, margin=dict(l=5, r=5, b=5, t=5), template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# --- 8. 8분할 매수 버튼 ---
logs = st.session_state.mock_data['logs']
next_step = len(logs) + 1
buy_amt = 1000000 if next_step == 1 else inv_p * (2/3)

if st.button(f"🔥 {next_step}차 거미줄 매수 실행 ({buy_amt:,.0f}원)", use_container_width=True, type="primary"):
    if yesu >= buy_amt:
        new_inv = inv_p + buy_amt
        new_avg = curr_price if avg_p == 0 else new_inv / ((inv_p/avg_p) + (buy_amt/curr_price))
        st.session_state.mock_data.update({"yesu": yesu - buy_amt, "inv_p": new_inv, "avg": new_avg})
        st.session_state.mock_data['logs'].append({'시간': datetime.now().strftime('%H:%M'), '차수': f"{next_step}차", '가격': f"{curr_price:,.0f}"})
        save_db(); st.balloons(); st.rerun()

# --- 9. 하단 매매 내역 ---
st.subheader("📋 최근 매매 내역")
if logs: st.table(pd.DataFrame(logs[::-1]))
else: st.caption("아직 기록이 없습니다.")

if st.button("♻️ 전체 데이터 초기화"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.session_state.clear(); st.rerun()

time.sleep(20); st.rerun()
