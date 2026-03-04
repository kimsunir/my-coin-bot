import streamlit as st
import pandas as pd
import ccxt
import json
import os
import plotly.graph_objects as go
from datetime import datetime

# --- 데이터 저장고 (파일 방식이라 새로고침 해도 유지됨!) ---
DB_FILE = "trading_v82.json"
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"yesu": 10000000, "invested_p": 0, "avg_price": 0, "logs": [], "run": False, "step": 0}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

d = load_data()

# --- 화면 설정 ---
st.set_page_config(page_title="코인 8분할 v0.82", layout="wide")
st.title("📊 8분할 거미줄 매매 시스템")

# --- 실시간 시세 (업비트) ---
try:
    upbit = ccxt.upbit()
    curr_price = upbit.fetch_ticker('BTC/KRW')['last']
except:
    curr_price = 0

# --- 실시간 자산 계산 ---
# 현재가치 = (투자원금 / 평단가) * 현재가
curr_value = (d['invested_p'] / d['avg_price'] * curr_price) if d['avg_price'] > 0 else 0
suik_geum = curr_value - d['invested_p']
suik_rate = (suik_geum / d['invested_p'] * 100) if d['invested_p'] > 0 else 0
total_asset = d['yesu'] + curr_value

# --- 1. 평단가 vs 현재가 차트 ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=["현재가/평단가"], y=[curr_price], mode="markers+text", name="현재가", text=["현재가"], textposition="top center", marker=dict(size=15, color="red")))
if d['avg_price'] > 0:
    fig.add_trace(go.Scatter(x=["현재가/평단가"], y=[d['avg_price']], mode="markers+text", name="내평단", text=["내평단"], textposition="bottom center", marker=dict(size=15, color="blue")))
fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10))
st.plotly_chart(fig, use_container_width=True)

# --- 2. 자산 현황판 ---
c1, c2, c3 = st.columns(3)
c1.metric("💰 총 자산", f"{total_asset:,.0f}원")
c2.metric("💵 예수금 (잔고)", f"{d['yesu']:,.0f}원")
c3.metric("📈 실시간 수익", f"{suik_geum:,.0f}원", f"{suik_rate:.2f}%")

# --- 3. 제어 버튼 ---
col_st, col_ed = st.columns(2)
if col_st.button("▶️ 자동매매 시작 (1차 매수)", use_container_width=True):
    if not d['run']:
        d['run'] = True
        amt = 1000000 # 1차 100만원 매수
        d['yesu'] -= amt
        d['invested_p'] = amt
        d['avg_price'] = curr_price
        d['step'] = 1
        d['logs'].append([datetime.now().strftime('%H:%M'), "1차 매수", f"{curr_price:,.0f}", "시작"])
        save_data(d)
        st.rerun()

if col_ed.button("⏹️ 전액 매도 및 정지", use_container_width=True):
    d.update({"yesu": total_asset, "invested_p": 0, "avg_price": 0, "run": False, "step": 0})
    d['logs'].append([datetime.now().strftime('%H:%M'), "전체종료", "청산완료", "정지"])
    save_data(d)
    st.rerun()

# --- 4. 매매 내역 ---
st.subheader("📝 최근 매매 기록")
if d['logs']:
    st.table(pd.DataFrame(d['logs'][::-1], columns=['시간', '작업', '가격', '비고']))
