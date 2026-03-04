import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import os

# --- 1. 설정 및 데이터 로드 ---
SAVE_FILE = "trading_data_v10.json"

def save_data(data):
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f)

def load_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            return json.load(f)
    return {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": [], "history": []}

# 데이터 초기화
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 2. 사이드바 (설정창) ---
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    
    # 모드 선택
    mode = st.toggle("🚀 실전 매매 모드 활성화", value=False)
    
    upbit = None
    if mode:
        st.info("실전 모드: 업비트 API 키를 입력하세요")
        access = st.text_input("Access Key", type="password")
        secret = st.text_input("Secret Key", type="password")
        if access and secret:
            try:
                upbit = ccxt.upbit({'apiKey': access, 'secret': secret, 'enableRateLimit': True})
                st.success("✅ 업비트 연결 성공 (실전)")
            except:
                st.error("❌ 키를 확인해주세요")
    else:
        st.write("현재: **모의 투자 모드 (검증용)**")

    st.divider()
    # 키보드 방지 라디오 버튼
    time_frame = st.radio("차트 시간", ['1m', '5m', '30m', '1h', '4h', '1d'], index=2)
    
    if st.button("⏹️ 전체 초기화"):
        if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
        st.session_state.clear()
        st.rerun()

# --- 3. 테마 및 상단 바 설정 ---
# 모드에 따라 핑크(모의) / 블루(실전) 테마 적용
main_color = "#3498db" if mode and upbit else "#ff69b4"
mode_text = "🔥 실전 매매 가동 중" if mode and upbit else "🌸 모의 투자 검증 중"

st.markdown(f"""
    <style>
    .stApp {{ border-top: 10px solid {main_color}; }}
    .mode-header {{ background-color: {main_color}; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom: 20px; }}
    </style>
    <div class="mode-header">{mode_text}</div>
    """, unsafe_allow_html=True)

# --- 4. 데이터 엔진 (실전 vs 모의) ---
try:
    public_upbit = ccxt.upbit()
    ticker = public_upbit.fetch_ticker('BTC/KRW')
    curr_price = ticker['last']
    
    if mode and upbit:
        # 실전 데이터 가져오기
        bal = upbit.fetch_balance()
        yesu = bal['KRW']['free']
        btc_bal = bal.get('BTC', {'total': 0, 'avgPrice': 0})
        inv_p = btc_bal['total'] * btc_bal['avgPrice']
        avg_price = btc_bal['avgPrice']
        total_asset = yesu + (btc_bal['total'] * curr_price)
    else:
        # 모의 데이터 사용
        yesu = st.session_state.data['yesu']
        inv_p = st.session_state.data['inv_p']
        avg_price = st.session_state.data['avg']
        total_asset = yesu + ( (inv_p / avg_price * curr_price) if avg_price > 0 else 0 )

    s_rate = ((curr_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
except:
    st.error("데이터를 불러오는 중입니다...")
    st.stop()

# --- 5. 대시보드 및 차트 ---
st.title("💰 거미줄 자동매매 시스템")

c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total_asset:,.0f}원")
c2.metric("💵 예수금", f"{yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

# 캔들 차트
ohlcv = public_upbit.fetch_ohlcv('BTC/KRW', timeframe=time_frame, limit=50)
df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
if avg_price > 0:
    fig.add_hline(y=avg_price, line_dash="dash", line_color="red", annotation_text="내 평단")
fig.update_layout(height=350, margin=dict(l=5, r=5, b=5, t=5), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# --- 6. 8분할 알고리즘 계산 및 매수 버튼 ---
st.divider()
# 1차 매수금 산정 (총자산의 5% 혹은 최소 100만원)
first_buy_unit = max(1000000, total_asset * 0.05) 

def calc_next_buy(logs, total_inv):
    step = len(logs) + 1
    if step == 1: return first_buy_unit
    return total_inv * (2/3)  # 언니의 황금 공식: 이전 총액의 2/3

next_buy_amt = calc_next_buy(st.session_state.data['logs'], inv_p)

if st.button(f"🚀 {len(st.session_state.data['logs'])+1}차 매수 실행 ({next_buy_amt:,.0f}원 투입)", use_container_width=True):
    if yesu >= next_buy_amt:
        new_inv = inv_p + next_buy_amt
        if avg_price == 0:
            new_avg = curr_price
        else:
            old_qty = inv_p / avg_price
            new_qty = next_buy_amt / curr_price
            new_avg = new_inv / (old_qty + new_qty)
        
        # 데이터 업데이트
        st.session_state.data['yesu'] -= next_buy_amt
        st.session_state.data['inv_p'] = new_inv
        st.session_state.data['avg'] = new_avg
        st.session_state.data['logs'].append({
            '시간': datetime.now().strftime('%H:%M:%S'),
            '차수': f"{len(st.session_state.data['logs'])+1}차",
            '가격': f"{curr_price:,.0f}원",
            '투입금': f"{next_buy_amt:,.0f}원"
        })
        save_data(st.session_state.data)
        st.balloons()
        st.rerun()

# --- 7. 매매 내역 및 자산 차트 ---
tab1, tab2 = st.tabs(["📋 매매 내역", "📉 자산 흐름"])
with tab1:
    if st.session_state.data['logs']:
        st.table(pd.DataFrame(st.session_state.data['logs'][::-1]))
with tab2:
    st.write("자산 변동 그래프가 준비 중입니다.")

# 10초 자동 갱신
time.sleep(10)
st.rerun()
