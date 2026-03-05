import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. 화면 설정 (지폴드7 최적화) ---
st.set_page_config(page_title="부석 거미줄 v35", layout="wide")

# 데이터 저장소 (세션)
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
if 'is_real' not in st.session_state:
    st.session_state.is_real = False

# --- 2. 사이드바 (모든 설정 모음) ---
with st.sidebar:
    st.title("⚙️ 설정")
    mode = st.radio("🏠 투자 모드 선택", ["🌸 모의투자", "🚀 실전투자"])
    st.session_state.is_real = (mode == "🚀 실전투자")
    
    st.divider()
    acc = st.text_input("Access Key", type="password", placeholder="여기에 입력")
    sec = st.text_input("Secret Key", type="password", placeholder="여기에 입력")
    
    if st.button("🔄 전체 초기화", use_container_width=True):
        st.session_state.mock_data = {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}
        st.rerun()

# --- 3. 데이터 엔진 (에러 방어막 설치) ---
display_total, display_cash, display_avg, curr_p = 10000000, 10000000, 0, 0

try:
    # 시세는 공용 API로 먼저 가져오기
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    
    if st.session_state.is_real and acc and sec:
        try:
            up_real = ccxt.upbit({'apiKey': acc, 'secret': sec})
            bal = up_real.fetch_balance()
            r_cash = float(bal.get('KRW', {}).get('free', 0))
            r_btc = float(bal.get('BTC', {}).get('total', 0))
            r_avg = next((float(i['avg_buy_price']) for i in bal['info'] if i['currency'] == 'BTC'), 0)
            
            display_total = r_cash + (r_btc * curr_p)
            display_cash, display_avg = r_cash, r_avg
        except:
            st.sidebar.error("⚠️ API 키가 틀렸거나 주소가 미등록 상태입니다.")
    else:
        # 모의투자 계산
        m = st.session_state.mock_data
        display_total = m['yesu'] + ((m['inv_p'] / m['avg'] * curr_p) if m['avg'] > 0 else 0)
        display_cash, display_avg = m['yesu'], m['avg']

except Exception as e:
    st.error("📡 인터넷 연결이 불안정합니다. 새로고침 하세요.")

# --- 4. 메인 대시보드 (지폴드 가로폭 활용) ---
st.title("💎 부석 거미줄 v35")
a, b, c = st.columns(3)
a.metric("🏦 총 자산", f"{display_total:,.0f}원")
b.metric("💵 현금 잔고", f"{display_cash:,.0f}원")
c.metric("🎯 평단가", f"{display_avg:,.0f}원")

# 매수 버튼
step = len(st.session_state.mock_data['logs']) + 1
if st.button(f"🔥 {step}차 매수 실행 (1,111,111원)", use_container_width=True, type="primary"):
    if display_cash >= 1111111:
        # 실전이면 주문 넣기
        if st.session_state.is_real and acc and sec:
            try: up_real.create_market_buy_order('BTC/KRW', 1111111)
            except: st.error("실전 주문 실패!")
        
        # 모의 기록 업데이트
        m = st.session_state.mock_data
        new_inv = m['inv_p'] + 1111111
        m['avg'] = curr_p if m['avg'] == 0 else new_inv / ((m['inv_p']/m['avg']) + (1111111/curr_p))
        m['yesu'] -= 1111111
        m['inv_p'] = new_inv
        m['logs'].append({'시간': datetime.now().strftime('%H:%M:%S'), '차수': f"{step}차", '가격': curr_p})
        st.balloons(); st.rerun()

# --- 5. 탭 구성 (수익 차트 포함!) ---
st.divider()
t1, t2, t3 = st.tabs(["📊 시세 차트", "📈 수익 곡선", "📋 매매 기록"])

with t1:
    tf = st.selectbox("분봉 선택", ["1m", "5m", "30m", "1h", "1d"], index=2)
    ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
    fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['time'], unit='ms'), open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    if display_avg > 0:
        fig.add_hline(y=display_avg, line_dash="dash", line_color="yellow", annotation_text="내 평단")
    fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

with t2:
    if st.session_state.mock_data['logs']:
        st.subheader("🚀 매수 흐름도")
        st.line_chart(pd.DataFrame(st.session_state.mock_data['logs']).set_index('시간')['가격'])
    else:
        st.info("매수 버튼을 누르면 수익 차트가 여기에 그려집니다.")

with t3:
    if st.session_state.mock_data['logs']:
        st.table(pd.DataFrame(st.session_state.mock_data['logs'][::-1]))
    else:
        st.info("매수 내역이 아직 없습니다.")

time.sleep(20); st.rerun()
