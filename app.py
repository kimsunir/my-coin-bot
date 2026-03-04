import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime
import time

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="코인 무적 엔진 v4.0", layout="wide")
st.title("💰 8분할 거미줄 자동매매 시스템")

# 2. 새로고침해도 데이터 유지하는 마법 (Session State)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000
if 'inv_p' not in st.session_state: st.session_state.inv_p = 0
if 'avg' not in st.session_state: st.session_state.avg = 0
if 'logs' not in st.session_state: st.session_state.logs = []
if 'price_history' not in st.session_state: st.session_state.price_history = []

# 3. 실시간 가격 및 히스토리 저장
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    price = ticker['last']
    st.session_state.price_history.append(price)
    if len(st.session_state.price_history) > 20: # 차트에는 최근 20개만 표시
        st.session_state.price_history.pop(0)
    st.success(f"✅ 연결 성공 | 현재가: {price:,.0f}원")
except:
    price = 0
    st.error("❌ 거래소 연결 대기 중...")

# 4. 자산 및 수익 계산
curr_v = (st.session_state.inv_p / st.session_state.avg * price) if st.session_state.avg > 0 else 0
s_rate = ((price - st.session_state.avg) / st.session_state.avg * 100) if st.session_state.avg > 0 else 0
total = st.session_state.yesu + curr_v

# 5. [차트 1] 코인 현황 실시간 차트
st.subheader("📈 비트코인 가격 흐름 (실시간)")
if st.session_state.price_history:
    chart_data = pd.DataFrame(st.session_state.price_history, columns=['Price'])
    st.line_chart(chart_data, height=200)

# 6. 상단 대시보드
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total:,.0f}원")
c2.metric("💵 예수금", f"{st.session_state.yesu:,.0f}원")
c3.metric("📊 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

# 7. [차트 2] 수익률 지표 바 (시각화)
st.write("**📊 수익률 지표 현황**")
st.progress(min(max((s_rate + 10) / 20, 0.0), 1.0)) # -10% ~ +10% 범위를 바 형태로 표시

st.divider()

# 8. 매매 로직 (버튼 클릭 시 데이터 즉시 반영)
col_buy, col_reset = st.columns([3, 1])

with col_buy:
    # 8분할 로직에 따른 버튼 노출 (예시: 1차)
    if st.button("🚀 매수 실행 (100만원 투입)", use_container_width=True):
        if st.session_state.yesu >= 1000000:
            # 평단가 계산 (물타기 공식)
            if st.session_state.avg == 0:
                st.session_state.avg = price
            else:
                old_q = st.session_state.inv_p / st.session_state.avg
                new_q = 1000000 / price
                st.session_state.avg = (st.session_state.inv_p + 1000000) / (old_q + new_q)
            
            st.session_state.yesu -= 1000000
            st.session_state.inv_p += 1000000
            st.session_state.logs.append([datetime.now().strftime('%H:%M:%S'), "매수", f"{price:,.0f}원"])
            st.balloons()
            st.rerun()

with col_reset:
    if st.button("⏹️ 데이터 리셋", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 9. 매매 기록 테이블
if st.session_state.logs:
    st.subheader("📅 매매 기록")
    st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '체결가']))

# 자동 새로고침 (5초마다 가격 갱신)
time.sleep(5)
st.rerun()
