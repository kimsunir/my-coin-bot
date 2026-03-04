import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import os

# --- 1. 저장 시스템 (절대 보존) ---
DB_FILE = "trading_db_v14.json"

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

# --- 2. 테마 및 레이아웃 ---
theme_color = "#3498db" if st.session_state.is_real else "#ff69b4"
st.set_page_config(page_title="거미줄 v14", layout="wide")
st.markdown(f"<style>.stApp {{ border-top: 15px solid {theme_color}; }} .stButton>button {{ border-radius: 12px; font-weight: bold; }}</style>", unsafe_allow_html=True)

# --- 3. 상단 모드 전환 ---
st.title("💎 부석 8분할 거미줄 시스템")
m1, m2 = st.columns(2)
with m1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="secondary" if st.session_state.is_real else "primary"):
        st.session_state.is_real = False
        save_db(); st.rerun()
with m2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.is_real else "secondary"):
        st.session_state.is_real = True
        save_db(); st.rerun()

# --- 4. 데이터 로직 (에러가 나도 차트는 보이게!) ---
upbit = None
error_msg = ""
try:
    public_upbit = ccxt.upbit()
    ticker = public_upbit.fetch_ticker('BTC/KRW')
    curr_price = ticker['last']
    
    # 실전 모드 연결 시도
    if st.session_state.is_real and st.session_state.access:
        try:
            upbit = ccxt.upbit({'apiKey': st.session_state.access, 'secret': st.session_state.secret, 'enableRateLimit': True})
            bal = upbit.fetch_balance()
            yesu = bal['KRW']['free']
            btc = bal.get('BTC', {'total': 0, 'avgPrice': 0})
            inv_p = btc['total'] * btc['avgPrice']
            avg_p = btc['avgPrice']
        except Exception as e:
            error_msg = f"⚠️ 업비트 연동 대기 중: {str(e)}"
            # 연동 실패 시 화면이 멈추지 않게 모의 데이터 임시 사용
            yesu, inv_p, avg_p = st.session_state.mock_data['yesu'], st.session_state.mock_data['inv_p'], st.session_state.mock_data['avg']
    else:
        yesu, inv_p, avg_p = st.session_state.mock_data['yesu'], st.session_state.mock_data['inv_p'], st.session_state.mock_data['avg']

    total_a = yesu + ( (inv_p / avg_p * curr_price) if avg_p > 0 else 0 )
    s_rate = ((curr_price - avg_p) / avg_p * 100) if avg_p > 0 else 0
except:
    st.warning("데이터 연결 중...")
    time.sleep(2); st.rerun()

# --- 5. 실전 설정창 (IP 에러 해결 가이드 추가) ---
if st.session_state.is_real:
    with st.expander("🔑 업비트 실전 연동 설정", expanded=(not upbit)):
        if "no_authorization_ip" in error_msg:
            st.error("🚨 [필수 해결] 업비트 홈페이지 -> 마이페이지 -> API 관리에서 'IP 등록'을 해제하거나 현재 기기의 IP를 추가해야 합니다!")
        elif error_msg: st.warning(error_msg)
        
        st.session_state.access = st.text_input("Access Key", value=st.session_state.access, type="password")
        st.session_state.secret = st.text_input("Secret Key", value=st.session_state.secret, type="password")
        if st.button("🔌 설정 저장 및 연결하기", use_container_width=True):
            save_db(); st.rerun()

# --- 6. 대시보드 (이제 무조건 보임!) ---
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total_a:,.0f}원")
c2.metric("💵 예수금", f"{yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

# 차트 영역
st.write("⏱️ **차트 시간 선택**")
tf = st.segmented_control("TF", ['1m', '5m', '30m', '1h', '4h', '1d'], default='30m', key="v14_tf")
ohlcv = public_upbit.fetch_ohlcv('BTC/KRW', timeframe=tf or '30m', limit=50)
df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
if avg_p > 0: fig.add_hline(y=avg_p, line_dash="dash", line_color="red", annotation_text="내 평단")
fig.update_layout(height=350, margin=dict(l=5, r=5, b=5, t=5), template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# --- 7. 매수 버튼 ---
st.divider()
logs = st.session_state.mock_data['logs']
next_step = len(logs) + 1
buy_amt = 1000000 if next_step == 1 else inv_p * (2/3)

if st.button(f"🔥 {next_step}차 거미줄 매수 실행 ({buy_amt:,.0f}원)", use_container_width=True, type="primary"):
    if yesu >= buy_amt:
        # 매매 로직 (생략 방지를 위해 이전 로직 유지)
        new_inv = inv_p + buy_amt
        new_avg = curr_price if avg_p == 0 else new_inv / ((inv_p/avg_p) + (buy_amt/curr_price))
        st.session_state.mock_data.update({"yesu": yesu - buy_amt, "inv_p": new_inv, "avg": new_avg})
        st.session_state.mock_data['logs'].append({'시간': datetime.now().strftime('%H:%M'), '차수': f"{next_step}차", '가격': f"{curr_price:,.0f}"})
        save_db(); st.balloons(); st.rerun()

# --- 8. 하단 기록표 ---
st.subheader("📋 최근 매매 내역")
if logs: st.table(pd.DataFrame(logs[::-1]))
else: st.caption("아직 기록이 없습니다.")

if st.button("♻️ 전체 초기화", use_container_width=True):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.session_state.clear(); st.rerun()

time.sleep(20); st.rerun()
