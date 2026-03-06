import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime

1. 지폴드 화면 설정
st.set_page_config(page_title="거미줄 v39", layout="wide")

데이터 저장 (없으면 만들기)
if 'm' not in st.session_state:
    st.session_state.m = {"y": 10000000, "inv": 0, "avg": 0, "logs": []}
if 'real' not in st.session_state:
    st.session_state.real = False

2. 사이드바 (지폴드 기럭지 활용)
with st.sidebar:
    st.header("⚙️ 설정")
    st.session_state.real = st.checkbox("🚀 실전모드 작동")
    if st.button("🔄 전체 초기화"):
        st.session_state.m = {"y": 10000000, "inv": 0, "avg": 0, "logs": []}
        st.rerun()
    st.divider()
    acc = st.text_input("Access Key", type="password")
    sec = st.text_input("Secret Key", type="password")

3. 데이터 로직 (실전/모의 합산)
try:
    up = ccxt.upbit()
    curr_p = up.fetch_ticker('BTC/KRW')['last']
자산 계산
    if st.session_state.real and acc and sec:
        try:
            r_up = ccxt.upbit({'apiKey': acc, 'secret': sec})
            bal = r_up.fetch_balance()
            cash = float(bal'KRW')
            btc_val = float(bal'BTC') * curr_p
            avg_p = next((float(i['avg_buy_price']) for i in bal['info'] if i['currency'] == 'BTC'), 0)
            total = cash + btc_val
        except: cash, avg_p, total = 0, 0, 0
    else:
        m = st.session_state.m
        cash, avg_p = m['y'], m['avg']
        total = cash + ((m['inv']/avg_p*curr_p) if avg_p > 0 else 0)

4. 메인 화면 출력
    st.title("💎 부석 거미줄 v39")
    a, b, c = st.columns(3)
    a.metric("🏦 총자산", f"{total:,.0f}")
    b.metric("💵 현금", f"{cash:,.0f}")
    c.metric("🎯 평단", f"{avg_p:,.0f}")

매수 버튼 (8분할 알고리즘)
    step = len(st.session_state.m['logs']) + 1
    if st.button(f"🔥 {step}차 매수 실행 (1,111,111원)", use_container_width=True, type="primary"):
        if cash >= 1111111:
            if st.session_state.real: # 실제 주문
                r_up.create_market_buy_order('BTC/KRW', 1111111)
기록 업데이트
            m = st.session_state.m
            new_inv = m['inv'] + 1111111
            m['avg'] = curr_p if m['avg']==0 else new_inv / ((m['inv']/m['avg']) + (1111111/curr_p))
            m['y'] = cash - 1111111
            m['inv'] = new_inv
            m['logs'].append({'시간': datetime.now().strftime('%H:%M'), '가격': curr_p})
            st.rerun()

5. 탭 구성
    t1, t2 = st.tabs(["📊 차트 & 평단선", "📋 매수 기록"])
    with t1:
        tf = st.radio("분봉", ["1m", "5m", "30m", "1h"], index=2, horizontal=True)
        ohlcv = up.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['t'], unit='ms'), open=df['o'], high=df['h'], low=df['l'], close=df['c'])])
        if avg_p > 0: # 노란 평단선!
            fig.add_hline(y=avg_p, line_dash="dash", line_color="yellow")
        fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)
    with t2:
        if st.session_state.m

except Exception as e:
    st.warning("📡 연결 중...")

내가만든 모바일 자동매매 프로그램 인데 
버젼을 보면 알다시피 30번 넘게 업그레이드를 했는데도 

1. 나는 지폴더 7 이라 기럭지가 잛아그래서 사이드 바가 필요해 ㅠ.ㅜ
2. 새로고침 초기화
3. 매수금액 이상해 1차 2차 3차 매수 금액이 같고
알고리즘 안돌아간것같아
4. 매수 수익 차트 분봉 버튼 안보여 코인현황에는 보이는데
5. 코인 현현황차트에 평균 매수금액 안보여 ㅠ.ㅜ
6.아직 실전 투자에서 업비트 투자 금액 못가져오고 있어
7.실전 매매은 업비트에서 하레
그런. 난 이거 왜 난들고 있겠어 ㅠ ㅜ
요렇게 우리우리가 고생점 하자 ㅜ.ㅠ
