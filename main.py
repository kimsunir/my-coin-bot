import streamlit as st
import pandas as pd
import ccxt
import json
import os
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 데이터 저장/불러오기 ---
DB_FILE = "trade_v8.json"
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"yesu": 10000000, "invested_principal": 0, "avg_price": 0, "logs": [], "run": False, "step": 0, "history": []}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

d = load_data()

# --- 화면 설정 ---
st.set_page_config(page_title="코인 8분할 v0.8", layout="wide")
st.title("📊 8분할 전략 대시보드")

# --- 실시간 데이터 ---
upbit = ccxt.upbit()
ticker = upbit.fetch_ticker('BTC/KRW')
curr_price = ticker['last']

# --- 금액 계산 ---
# 투자금의 현재 가치 = (투자원금 / 평단가) * 현재가 (평단가 0이면 0)
curr_value = (d['invested_principal'] / d['avg_price'] * curr_price) if d['avg_price'] > 0 else 0
suik_geum = curr_value - d['invested_principal']
suik_율 = (suik_geum / d['invested_principal'] * 100) if d['invested_principal'] > 0 else 0
total_asset = d['yesu'] + curr_value

# --- 상단: 실시간 평단가 현황 차트 ---
fig_ptr = go.Figure()
fig_ptr.add_trace(go.Scatter(x=["현재 상태"], y=[curr_price], mode="markers+text", name="현재가", text=["현재가"], textposition="top center", marker=dict(size=15, color="red")))
if d['avg_price'] > 0:
    fig_ptr.add_trace(go.Scatter(x=["현재 상태"], y=[d['avg_price']], mode="markers+text", name="평단가", text=["내 평단"], textposition="bottom center", marker=dict(size=15, color="blue")))
fig_ptr.update_layout(title="📈 현재가 vs 내 평단 위치", height=300, yaxis_title="가격(KRW)")
st.plotly_chart(fig_ptr, use_container_width=True)

# --- 중단: 자산 현황판 ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("총 자산", f"{total_asset:,.0f}원")
c2.metric("예수금 (잔고)", f"{d['yesu']:,.0f}원")
c3.metric("수익금", f"{suik_geum:,.0f}원", f"{suik_율:.2f}%")
c4.metric("현재가", f"{curr_price:,.0f}")

# --- 제어 버튼 ---
col_bt1, col_bt2 = st.columns(2)
if col_bt1.button("▶️ 자동매매 시작 (1차 매수)", use_container_width=True):
    if not d['run']:
        d['run'] = True
        buy_amt = 1000000 # 100만원 1차 매수
        d['yesu'] -= buy_amt
        d['invested_principal'] = buy_amt
        d['avg_price'] = curr_price
        d['step'] = 1
        d['logs'].append([datetime.now().strftime('%m/%d %H:%M'), "1차매수", f"{curr_price:,.0f}", "시작"])
        save_data(d)
        st.rerun()

if col_bt2.button("⏹️ 전체종료 (전액매도)", use_container_width=True):
    d.update({"yesu": total_asset, "invested_principal": 0, "avg_price": 0, "run": False, "step": 0})
    d['logs'].append([datetime.now().strftime('%m/%d %H:%M'), "전체종료", "매도완료", "정지"])
    save_data(d)
    st.rerun()

# --- 하단: 기간별 수익 추이 차트 ---
st.divider()
st.subheader("📉 수익 추이 분석")
period = st.radio("기간 선택", ["5분", "30분", "1시간", "4시간", "일자별"], horizontal=True)

# (시뮬레이션 데이터 생성 - 실제론 데이터가 쌓여야 함)
chart_data = pd.DataFrame({
    'time': [datetime.now() - timedelta(minutes=i*5) for i in range(10)],
    'profit': [suik_geum - (i*1000) for i in range(10)]
})
fig_hist = go.Figure(go.Scatter(x=chart_data['time'], y=chart_data['profit'], fill='tozeroy', name="수익금"))
fig_hist.update_layout(height=300, title=f"{period} 기준 수익 흐름")
st.plotly_chart(fig_hist, use_container_width=True)

# --- 최하단: 매매 기록 ---
with st.expander("📝 상세 매매 기록 보기"):
    if d['logs']:
        st.table(pd.DataFrame(d['logs'][::-1], columns=['시간', '작업', '가격', '상태']))
