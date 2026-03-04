import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime
import time

# 1. 페이지 설정
st.set_page_config(page_title="코인 무적 엔진 v5.0", layout="wide")
st.title("💰 8분할 거미줄 자동매매 시스템")

# 2. 새로고침 방지용 데이터 저장소 (세션 상태)
if 'yesu' not in st.session_state: st.session_state.yesu = 10000000
if 'inv_p' not in st.session_state: st.session_state.inv_p = 0
if 'avg' not in st.session_state: st.session_state.avg = 0
if 'logs' not in st.session_state: st.session_state.logs = []

# 3. 사이드바 - 차트 시간 선택 (콤보박스)
with st.sidebar:
    st.header("⚙️ 차트 설정")
    time_frame = st.selectbox("차트 시간 선택", ['1m', '5m', '30m', '1h', '4h', '1d'], index=0)
    st.info("선택한 시간에 따라 차트가 갱신됩니다.")

# 4. 실시간 데이터 가져오기 (업비트)
try:
    upbit = ccxt.upbit()
    # 캔들 데이터 (OHLCV) 가져오기
    ohlcv = upbit.fetch_ohlcv('BTC/KRW', timeframe=time_frame, limit=50)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=9) # 한국 시간
    
    curr_price = df['close'].iloc[-1]
    st.success(f"✅ 업비트 연결 중 | 현재가: {curr_price:,.0f}원")
except:
    st.error("❌ 거래소 데이터를 가져오는 중입니다...")
    st.stop()

# 5. 자산 계산
curr_v = (st.session_state.inv_p / st.session_state.avg * curr_price) if st.session_state.avg > 0 else 0
s_rate = ((curr_price - st.session_state.avg) / st.session_state.avg * 100) if st.session_state.avg > 0 else 0
total = st.session_state.yesu + curr_v

# 6. [차트] 실시간 가격 흐름 + 내 평균 매수가 표시
st.subheader(f"📈 비트코인 {time_frame} 차트")
# 내 평균 매수가 컬럼 추가
df['평균매수가'] = st.session_state.avg if st.session_state.avg > 0 else None

# 라인 차트 표시 (현재가와 내 평단가 비교)
chart_df = df.set_index('timestamp')[['close', '평균매수가']]
st.line_chart(chart_df)

# 7. 대시보드
c1, c2, c3 = st.columns(3)
c1.metric("🏦 총 자산", f"{total:,.0f}원")
c2.metric("💵 예수금", f"{st.session_state.yesu:,.0f}원")
c3.metric("📊 수익률", f"{s_rate:.2f}%", delta=f"{s_rate:.2f}%")

st.write("**📊 수익률 지표 현황**")
st.progress(min(max((s_rate + 10) / 20, 0.0), 1.0))

st.divider()

# 8. 매매 버튼
col1, col2 = st.columns([3, 1])
with col1:
    if st.button(f"🚀 {len(st.session_state.logs)+1}차 매수 실행 (100만원)", use_container_width=True):
        if st.session_state.yesu >= 1000000:
            if st.session_state.avg == 0:
                st.session_state.avg = curr_price
            else:
                old_q = st.session_state.inv_p / st.session_state.avg
                new_q = 1000000 / curr_price
                st.session_state.avg = (st.session_state.inv_p + 1000000) / (old_q + new_q)
            
            st.session_state.yesu -= 1000000
            st.session_state.inv_p += 1000000
            st.session_state.logs.append([datetime.now().strftime('%H:%M:%S'), f"{len(st.session_state.logs)+1}차 매수", f"{curr_price:,.0f}원"])
            st.balloons()
            st.rerun()

with col2:
    if st.button("⏹️ 전체 초기화", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 9. 매매 기록
if st.session_state.logs:
    st.subheader("📅 매매 기록")
    st.table(pd.DataFrame(st.session_state.logs[::-1], columns=['시간', '작업', '체결가']))

# 10초마다 자동 갱신
time.sleep(10)
st.rerun()
