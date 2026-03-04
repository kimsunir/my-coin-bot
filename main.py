import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime

st.set_page_config(page_title="코인 8분할 v0.3")

# 1. 초기 설정
if 'balance' not in st.session_state: st.session_state.balance = 10000000
if 'run' not in st.session_state: st.session_state.run = False
if 'logs' not in st.session_state: st.session_state.logs = []

# 2. 메인 화면
st.title("🟢 비트코인 8분할 매매")
st.write(f"### 💰 현재 자산: {st.session_state.balance:,.0f}원")

# 3. 가동 버튼
if st.button("▶️ 자동매매 시작", use_container_width=True):
    st.session_state.run = True
    now = datetime.now().strftime('%H:%M:%S')
    st.session_state.logs.append([now, "BTC", "감시시작", "연동완료", "0%"])
    st.success("매매 가동 중!")

if st.button("⏹️ 일시 정지", use_container_width=True):
    st.session_state.run = False
    st.warning("정지됨")

# 4. 실시간 시세
st.divider()
upbit = ccxt.upbit()
price = upbit.fetch_ticker('BTC/KRW')['last']
st.metric("현재 비트코인 시세", f"{price:,.0f} KRW")

# 5. 매매 기록 표
st.subheader("📅 매매 기록")
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '가격', '수익률'])
    st.table(df)
else:
    st.write("버튼을 누르면 기록이 뜹니다.")
    st.write("시세 로딩 중...")

# 6. 매수 단계 표시
st.write("🧩 매수 단계: " + "🟢" * st.session_state.buy + "⚪" * (8 - st.session_state.buy))

# 7. 기록 표
st.subheader("📅 매매 기록")
if len(st.session_state.logs) > 0:
    df = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '가격', '수익률'])
    st.table(df)
else:
    st.write("버튼을 누르면 기록이 뜹니다.")
except:
    st.write("시세를 불러오는 중입니다...")

# 6. 8분할 매수 상태
st.subheader("🧩 8분할 매수 단계")
cols = st.columns(4)
for i in range(8):
    with cols[i % 4]:
        if i < st.session_state.buy_count: st.success(f"{i+1}단계")
        else: st.info(f"{i+1}단계")

# 7. 매매 기록 표
st.subheader("📅 매매 기록")
if len(st.session_state.logs) > 0:
    df = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '가격', '수익률'])
    st.table(df)
else:
    st.write("시작 버튼을 눌러주세요.")
with col2:
    if st.button("⏹️ 일시 정지", use_container_width=True):
        st.session_state.is_running = False

# 5. 실시간 시세 (에러 방지 처리)
st.divider()
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    price = ticker['last']
    c1, c2 = st.columns(2)
    c1.metric("현재 BTC 가격", f"{price:,.0f} KRW")
    c2.metric("모의 잔고", f"{st.session_state.balance:,.0f} KRW")
except:
    st.warning("시세를 연결 중입니다...")

# 6. 8분할 매수 현황
st.subheader("🧩 8분할 매수 단계")
cols = st.columns(4)
for i in range(8):
    with cols[i % 4]:
        if i < st.session_state.buy_count:
            st.success(f"{i+1}단계")
        else:
            st.info(f"{i+1}단계")

# 7. 매매 내역 (기록이 있을 때만 표 표시)
st.subheader("📅 매매 기록")
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '가격', '수익률'])
    st.table(df)
else:
    st.write("시작 버튼을 누르면 기록이 나타납니다.")

st.caption("v0.15: 들여쓰기 오류 완전 방지 버전")
        st.session_state.logs.append([now, "BTC", "감시 시작", "연동 완료", "0%"])
        st.success("엔진 가동 시작!")
with col2:
    if st.button("⏹️ 일시 정지", use_container_width=True):
        st.session_state.is_running = False
        st.warning("엔진이 정지되었습니다.")

# --- 실시간 시세 및 잔고 ---
st.divider()
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    current_price = ticker['last']
    c1, c2 = st.columns(2)
    c1.metric("현재 BTC 가격", f"{current_price:,.0f} KRW")
    c2.metric("모의 투자 잔고", f"{st.session_state.balance:,.0f} KRW")
except:
    st.error("시세를 불러오는 중...")

# --- 8분할 매수 현황판 ---
st.subheader("🧩 8분할 매수 진행도")
cols = st.columns(4)
for i in range(8):
    with cols[i % 4]:
        if i < st.session_state.buy_count:
            st.success(f"{i+1}단계 완료")
        else:
            st.info(f"{i+1}단계 대기")

# --- 매매 로그 ---
st.subheader("📅 날짜별 매매 내역")
if len(st.session_state.logs) > 0:
    df_logs = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '가격', '수익률'])
    st.table(df_logs)
else:
    st.write("상단의 [시작] 버튼을 누르면 기록이 표시됩니다.")

st.caption("v0.12: 들여쓰기 에러 수정 및 안정화 버전")
        now = datetime.now().strftime('%H:%M:%S')
        st.session_state.logs.append([now, "BTC", "감시 시작", "연동 완료", "0%"])
        st.success("엔진 가동! 1,000만원 모의투자가 시작되었습니다.")
with col2:
    if st.button("⏹️ 일시 정지", use_container_width=True):
        st.session_state.is_running = False
        st.warning("엔진이 정지되었습니다.")

# --- 실시간 시세 및 잔고 ---
st.divider()
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    current_price = ticker['last']
    c1, c2 = st.columns(2)
    c1.metric("현재 BTC 가격", f"{current_price:,.0f} KRW")
    c2.metric("모의 투자 잔고", f"{st.session_state.balance:,.0f} KRW")
except:
    st.error("시세를 불러오는 중...")

# --- 8분할 매수 현황판 ---
st.subheader("🧩 8분할 매수 진행도")
cols = st.columns(4)
for i in range(8):
    with cols[i % 4]:
        if i < st.session_state.buy_count:
            st.success(f"{i+1}단계 완료")
        else:
            st.info(f"{i+1}단계 대기")

# --- 매매 로그 (에러 방지 처리 완료) ---
st.subheader("📅 날짜별 매매 내역")
if len(st.session_state.logs) > 0:
    df_logs = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '가격', '수익률'])
    st.table(df_logs)
else:
    st.write("상단의 [시작] 버튼을 누르면 매매 기록이 여기에 표시됩니다.")

st.caption("v0.11: 기록 없을 시 에러 방지 로직 적용")
    if st.button("⏹️ 일시 정지", use_container_width=True):
        st.session_state.is_running = False
        st.warning("엔진이 정지되었습니다.")

# --- 실시간 시세 및 잔고 ---
st.divider()
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    current_price = ticker['last']
    
    c1, c2 = st.columns(2)
    c1.metric("현재 BTC 가격", f"{current_price:,.0f} KRW")
    c2.metric("모의 투자 잔고", f"{st.session_state.balance:,.0f} KRW")
except:
    st.error("시세를 불러오는 중...")

# --- 8분할 매수 현황판 ---
st.subheader("🧩 8분할 매수 진행도")
if st.session_state.is_running:
    st.info(f"현재 비트코인 시세를 감시하며 8분할 전략을 실행 중입니다. (현재 {st.session_state.buy_count}단계)")
else:
    st.write("가동 버튼을 누르면 8분할 매수 로직이 시작됩니다.")

cols = st.columns(4)
for i in range(8):
    with cols[i % 4]:
        if i < st.session_state.buy_count:
            st.success(f"{i+1}단계 완료")
        else:
            st.info(f"{i+1}단계 대기")

# --- 수익률 그래프 ---
st.subheader("📈 수익률 추이")
chart_data = pd.DataFrame({'Profit(%)': [0, 0.2, -0.1, 0.5, 0.8]}, index=pd.date_range("2026-03-01", periods=5))
st.line_chart(chart_data)

st.caption("v0.1: 시작 버튼 및 1,000만원 잔고 연동 완료")

# 업비트 시세 가져오기 (ccxt 사용)
try:
    upbit = ccxt.upbit()
    ticker = upbit.fetch_ticker('BTC/KRW')
    current_price = ticker['last']
    st.metric("현재 비트코인(BTC) 가격", f"{current_price:,.0f} KRW")
except:
    st.error("시세를 불러오는 중입니다... 잠시만 기다려주세요.")
    current_price = 90000000 # 에러 시 임시 가격

# --- 8분할 매수 현황판 시각화 ---
st.write("🧩 **8분할 계단식 물타기 현황**")
cols = st.columns(4)
# 예시로 2단계까지 매수된 상황 가정
current_stage = 2 
for i in range(8):
    with cols[i % 4]:
        if i < current_stage:
            st.success(f"{i+1}단계 완료")
        else:
            st.info(f"{i+1}단계 대기")

# --- 수익률 차트 ---
chart_data = pd.DataFrame({'수익률(%)': [0, 0.5, -0.2, 1.2, 2.5]}, index=pd.date_range("2026-03-01", periods=5))
st.line_chart(chart_data)

# --- 매매 로그 검색 기능 ---
st.subheader("📅 날짜별 매매 내역")
search_date = st.date_input("조회 날짜", datetime.now())
df_logs = pd.DataFrame(st.session_state.logs, columns=['시간', '종목', '구분', '가격', '수익률'])
if df_logs.empty:
    st.write("해당 날짜에 매매 기록이 없습니다.")
else:
    st.table(df_logs)

# --- 하단 안내 ---
st.divider()
st.caption("v0.05: 실제 업비트 시세 연동 및 8분할 로직 뼈대 완성. 다음 버전에서 '자동 주문 버튼'이 활성화됩니다.")
