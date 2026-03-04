import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="코인 거미줄 v11", layout="wide")

# --- 데이터 유지 (모의투자용) ---
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False

# --- 테마 설정 (모드에 따른 색상 변화) ---
theme_color = "#3498db" if st.session_state.is_real else "#ff69b4"
bg_gradient = "linear-gradient(135deg, #1e3a8a, #3498db)" if st.session_state.is_real else "linear-gradient(135deg, #831843, #ff69b4)"

st.markdown(f"""
    <style>
    .main {{ background: #0e1117; }}
    div[data-testid="stMetricValue"] {{ color: {theme_color}; font-size: 1.8rem; font-weight: bold; }}
    .mode-indicator {{
        background: {bg_gradient};
        color: white; padding: 15px; border-radius: 15px; text-align: center;
        font-size: 1.2rem; font-weight: bold; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }}
    .stButton>button {{ border-radius: 20px; border: 1px solid {theme_color}; }}
    </style>
""", unsafe_allow_html=True)

# --- 상단 모드 전환 영역 ---
st.markdown(f'<div class="mode-indicator">{"🚀 실전 매매 운용 중" if st.session_state.is_real else "🌸 모의 투자 검증 중"}</div>', unsafe_allow_html=True)

m1, m2 = st.columns(2)
with m1:
    if st.button("🌸 모의투자 모드", use_container_width=True):
        st.session_state.is_real = False
        st.rerun()
with m2:
    if st.button("🚀 실전투자 모드", use_container_width=True):
        st.session_state.is_real = True

# 실전 모드 시 API 입력창 활성화
upbit = None
if st.session_state.is_real:
    with st.expander("🔑 업비트 API 키 설정 (보안 유지)", expanded=True):
        access = st.text_input("Access Key", type="password", placeholder="여기에 입력하세요")
        secret = st.text_input("Secret Key", type="password", placeholder="여기에 입력하세요")
        if access and secret:
            try:
                upbit = ccxt.upbit({'apiKey': access, 'secret': secret})
                st.success("✅ 실전 계좌 연결 성공!")
            except:
                st.error("❌ 키가 올바르지 않습니다.")
        else:
            st.warning("API 키를 입력해야 실전 잔고가 표시됩니다.")

# --- 데이터 엔진 ---
try:
    public_upbit = ccxt.upbit()
    ticker = public_upbit.fetch_ticker('BTC/KRW')
    curr_price = ticker['last']
    
    if st.session_state.is_real and upbit:
        bal = upbit.fetch_balance()
        yesu = bal['KRW']['free']
        btc_bal = bal.get('BTC', {'total': 0, 'avgPrice': 0})
        inv_p = btc_bal['total'] * btc_bal['avgPrice']
        avg_price = btc_bal['avgPrice']
    else:
        # 모의투자 데이터
        yesu = st.session_state.mock_data['yesu']
        inv_p = st.session_state.mock_data['inv_p']
        avg_price = st.session_state.mock_data['avg']
    
    total_asset = yesu + ( (inv_p / avg_price * curr_price) if avg_price > 0 else 0 )
    s_rate = ((curr_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
except:
    st.info("데이터를 불러오는 중...")
    st.stop()

# --- 메인 대시보드 ---
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total_asset:,.0f}원")
c2.metric("💵 예수금", f"{yesu:,.0f}원")
c3.metric("📈 수익률", f"{s_rate:.2f}%")

# --- 차트 시간 설정 (키보드 안 뜨는 방식) ---
st.write("⏱️ **차트 시간 단위 선택**")
time_frame = st.segmented_control(
    "시간단위", 
    options=['1m', '5m', '30m', '1h', '4h', '1d'], 
    default='30m',
    key="tf_choice"
)

# 차트 그리기
ohlcv = public_upbit.fetch_ohlcv('BTC/KRW', timeframe=time_frame or '30m', limit=50)
df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)
fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
if avg_price > 0:
    fig.add_hline(y=avg_price, line_dash="dash", line_color="red", annotation_text="내 평단")
fig.update_layout(height=350, margin=dict(l=10, r=10, b=10, t=10), template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# --- 8분할 매수 알고리즘 버튼 ---
st.divider()
logs = st.session_state.mock_data['logs']
next_step = len(logs) + 1
# 공식: 1차는 100만, 2차부터는 총 투입금의 2/3
buy_amt = 1000000 if next_step == 1 else inv_p * (2/3)

if st.button(f"🔥 {next_step}차 거미줄 매수 실행 ({buy_amt:,.0f}원)", use_container_width=True, type="primary"):
    if yesu >= buy_amt:
        # 매수 로직 (모의투자용 예시)
        new_inv = inv_p + buy_amt
        if avg_price == 0: new_avg = curr_price
        else:
            old_q = inv_p / avg_price
            new_q = buy_amt / curr_price
            new_avg = new_inv / (old_q + new_q)
        
        st.session_state.mock_data['yesu'] -= buy_amt
        st.session_state.mock_data['inv_p'] = new_inv
        st.session_state.mock_data['avg'] = new_avg
        st.session_state.mock_data['logs'].append({
            '시간': datetime.now().strftime('%H:%M'),
            '차수': f"{next_step}차",
            '투입금': f"{buy_amt:,.0f}",
            '상태': '완료'
        })
        st.toast(f"{next_step}차 매수 완료!")
        st.rerun()

# --- 매매 내역 표 ---
st.subheader("📋 매매 기록")
if logs:
    st.table(pd.DataFrame(logs[::-1]))
else:
    st.caption("기록이 없습니다.")

# 자동 갱신
time.sleep(10)
st.rerun()
