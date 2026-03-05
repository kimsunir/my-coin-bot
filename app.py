import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime

# 1. 화면 기본 설정
st.set_page_config(page_title="거미줄 v37", layout="wide")

# 데이터 저장 (꼬이지 않게 세션 고정)
if 'm' not in st.session_state:
    st.session_state.m = {"y": 10000000, "inv": 0, "avg": 0, "logs": []}

# 2. 모드 선택 및 초기화
st.title("💎 부석 거미줄 v37")
col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    is_real = st.toggle("🚀 실전투자 모드 켜기")
with col_opt2:
    if st.button("🔄 데이터 초기화"):
        st.session_state.m = {"y": 10000000, "inv": 0, "avg": 0, "logs": []}
        st.rerun()

# 3. 데이터 가져오기 (에러 방지)
try:
    up_pub = ccxt.upbit()
    curr_p = up_pub.fetch_ticker('BTC/KRW')['last']
    
    # 실전/모의 자산 계산
    if is_real:
        st.info("🔑 사이드바(왼쪽 >)에 API 키를 입력하면 실전 잔고가 나옵니다.")
        # 실전 기능은 키 입력시에만 활성화되도록 보호
        total, cash, avg_p = 0, 0, 0
    else:
        m = st.session_state.m
        total = m['y'] + ((m['inv']/m['avg']*curr_p) if m['avg']>0 else 0)
        cash, avg_p = m['y'], m['avg']

    # 4. 현황판 표시
    a, b, c = st.columns(3)
    a.metric("🏦 총 자산", f"{total:,.0f}원")
    b.metric("💵 현금 잔고", f"{cash:,.0f}원")
    c.metric("🎯 나의 평단", f"{avg_p:,.0f}원")

    # 5. 매수 버튼 (여기가 핵심!)
    step = len(st.session_state.m['logs']) + 1
    if st.button(f"🔥 {step}차 거미줄 매수 실행 (1,111,111원)", use_container_width=True, type="primary"):
        if cash >= 1111111:
            # 기록 업데이트
            m = st.session_state.m
            new_inv = m['inv'] + 1111111
            m['avg'] = curr_p if m['avg']==0 else new_inv / ((m['inv']/m['avg']) + (1111111/curr_p))
            m['y'] -= 1111111
            m['inv'] = new_inv
            m['logs'].append({'시간': datetime.now().strftime('%H:%M'), '가격': curr_p})
            st.balloons(); st.rerun()

    # 6. 탭 구성 (차트와 기록)
    t1, t2 = st.tabs(["📊 차트 & 평단선", "📋 매매 기록표"])
    
    with t1:
        tf = st.radio("분봉", ["1m", "5m", "30m", "1h"], index=2, horizontal=True)
        ohlcv = up_pub.fetch_ohlcv('BTC/KRW', timeframe=tf, limit=50)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        fig = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['t'], unit='ms'), open=df['o'], high=df['h'], low=df['l'], close=df['c'])])
        if avg_p > 0:
            fig.add_hline(y=avg_p, line_dash="dash", line_color="yellow")
        fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        if st.session_state.m['logs']:
            st.table(pd.DataFrame(st.session_state.m['logs'][::-1]))
        else:
            st.info("매수 버튼을 누르면 기록이 남습니다.")

except Exception as e:
    st.error(f"📡 연결 오류: {e}")
