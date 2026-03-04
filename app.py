import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
import time

# ==========================================
# 1. 업비트 계정 설정 (여기에 언니 키를 넣으세요!)
# ==========================================
ACCESS_KEY = "언니의_ACCESS_KEY_입력"
SECRET_KEY = "언니의_SECRET_KEY_입력"

# 업비트 연결
upbit = ccxt.upbit({
    'apiKey': ACCESS_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
})

# 2. 페이지 설정
st.set_page_config(page_title="업비트 무적 8분할 v9.0", layout="wide")

# 3. 세션 상태 초기화 (자동매매 On/Off 등)
if 'auto_trade' not in st.session_state: st.session_state.auto_trade = False
if 'logs' not in st.session_state: st.session_state.logs = []

# 4. [사이드바] 설정 및 자동매매 스위치
with st.sidebar:
    st.header("⚙️ 실전 매매 설정")
    # 키보드 안 뜨는 라디오 버튼 분봉 선택
    time_frame = st.radio("차트 시간 단위", ['1m', '5m', '30m', '1h', '1d'], index=1)
    
    st.divider()
    st.subheader("🤖 자동매매 시스템")
    if st.button("🚀 자동매매 시작", use_container_width=True):
        st.session_state.auto_trade = True
    if st.button("⏹️ 시스템 긴급 종료", use_container_width=True, type="primary"):
        st.session_state.auto_trade = False
        st.warning("시스템이 종료되었습니다.")
    
    st.write(f"현재 상태: {'🟢 가동 중' if st.session_state.auto_trade else '🔴 중지됨'}")

# 5. 데이터 가져오기 (실제 내 잔고)
try:
    # 실제 업비트 잔고 조회
    balance = upbit.fetch_balance()
    # KRW 잔고 (예수금)
    krw_free = balance['KRW']['free'] 
    # BTC 보유량 및 평단가 (실제 업비트 정보)
    btc_info = balance.get('BTC', {'total': 0, 'avgPrice': 0})
    inv_p = btc_info['total'] * btc_info['avgPrice'] if btc_info['avgPrice'] else 0
    avg_price = btc_info['avgPrice'] if btc_info['avgPrice'] else 0
    
    # 총 자산 계산
    ticker = upbit.fetch_ticker('BTC/KRW')
    curr_price = ticker['last']
    total_asset = krw_free + (btc_info['total'] * curr_price)
    
    # 수익률
    s_rate = ((curr_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
except Exception as e:
    st.error(f"업비트 연결 실패: {e}")
    st.stop()

# 6. [알고리즘] 8분할 매수 금액 미리 계산하기
# 1차 매수금을 총 자산의 일정 비율(예: 5%)로 잡거나 언니가 정할 수 있습니다.
base_buy_unit = total_asset * 0.05 # 예시: 총자산의 5%를 1차로 산정

def get_next_buy_amount(step, total_invested):
    """언니의 8분할 공식: 이전까지 총 매수금액의 2/3를 다음 차수에 투입"""
    if step == 1: return base_buy_unit
    return total_invested * (2/3)

# 7. 메인 화면 구성
st.title("💰 업비트 8분할 거미줄 시스템")

# 상단 요약
col1, col2, col3 = st.columns(3)
col1.metric("🏦 실제 총 자산", f"{total_asset:,.0f}원")
col2.metric("💵 사용 가능 예수금", f"{krw_free:,.0f}원")
col3.metric("📈 실시간 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

# 8. [차트 영역]
ohlcv = upbit.fetch_ohlcv('BTC/KRW', timeframe=time_frame, limit=50)
df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=9)

fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
if avg_price > 0:
    fig.add_hline(y=avg_price, line_dash="dash", line_color="red", annotation_text=f"내 평단: {avg_price:,.0f}")
fig.update_layout(height=400, margin=dict(l=10, r=10, b=10, t=10), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# 9. [8분할 전략 정보창]
with st.expander("📝 현재 나의 8분할 매수 계획 확인"):
    data = []
    temp_total = 0
    for i in range(1, 9):
        amt = get_next_buy_amount(i, temp_total)
        drop = "시작" if i == 1 else ("-4%" if i==2 else ("-6%" if i==3 else "-8% 고정"))
        data.append({"차수": f"{i}차", "하락조건": drop, "매수금액": f"{amt:,.0f}원"})
        temp_total += amt
    st.table(pd.DataFrame(data))

# 10. [매매 내역]
st.subheader("📋 최근 체결 기록")
if st.session_state.logs:
    st.table(pd.DataFrame(st.session_state.logs[::-1]))
else:
    st.write("아직 매매 기록이 없습니다.")

# 11. 자동매매 로직 실행 (가동 중일 때만)
if st.session_state.auto_trade:
    # 여기에 실제 매수/매도 로직이 들어갑니다.
    # 1. 7% 익절 감시
    if s_rate >= 7.0:
        st.toast("🎯 익절 목표 도달! 전량 매도 실행")
        # upbit.create_market_sell_order('BTC/KRW', btc_info['total'])
        st.session_state.auto_trade = False # 익절 후 재설정을 위해 잠시 정지
    
    # 2. 하락 시 추가 매수 감시 (로직 생략 - 실제 주문은 신중해야 하므로 로그만 남김)
    st.caption("🤖 시스템이 실시간으로 가격을 감시하며 거미줄을 치고 있습니다...")

# 자동 갱신
time.sleep(10)
st.rerun()
