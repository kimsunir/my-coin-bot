import streamlit as st
import pandas as pd
import ccxt
import json
import os
from datetime import datetime

# --- 데이터 저장고 (파일 방식) ---
DB_FILE = "trade_v90.json"
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"yesu": 10000000, "invested_p": 0, "avg_price": 0, "logs": [], "run": False, "step": 0}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

d = load_data()

# --- 화면 설정 (가장 가벼운 방식) ---
st.set_page_config(page_title="코인 8분할 v0.9")
st.title("📊 8분할 거미줄 매매 엔진")

# --- 실시간 시세 조회 ---
try:
    upbit = ccxt.upbit()
    curr_price = upbit.fetch_ticker('BTC/KRW')['last']
except:
    curr_price = 0

# --- 실시간 자산 계산 ---
curr_val = (d['invested_p'] / d['avg_price'] * curr_price) if d['avg_price'] > 0 else 0
suik_geum = curr_val - d['invested_p']
suik_rate = (suik_geum / d['invested_p'] * 100) if d['invested_p'] > 0 else 0
total_asset = d['yesu'] + curr_val

# --- 자산 현황판 (차트 없이 텍스트로 깔끔하게) ---
st.success(f"💰 총 자산: {total_asset:,.0f}원")
c1, c2 = st.columns(2)
c1.metric("💵 예수금 (잔고)", f"{d['yesu']:,.0f}원")
c2.metric("📈 수익금", f"{suik_geum:,.0f}원", f"{suik_rate:.2f}%")

st.info(f"📍 현재가: {curr_price:,.0f}원 | 🔵 내 평단: {d['avg_price']:,.0f}원")

# --- 제어 버튼 ---
col_st, col_ed = st.columns(2)
if col_st.button("▶️ 자동매매 시작 (1차 매수)", use_container_width=True):
    if not d['run']:
        d['run'] = True
        amt = 1000000 # 1차 100만원
        d['yesu'] -= amt
        d['invested_p'] = amt
        d['avg_price'] = curr_price
        d['step'] = 1
        d['logs'].append([datetime.now().strftime('%H:%M'), "1차 매수", f"{curr_price:,.0f}", "시작"])
        save_data(d)
        st.rerun()

if col_ed.button("⏹️ 전체종료 및 청산", use_container_width=True):
    d.update({"yesu": total_asset, "invested_p": 0, "avg_price": 0, "run": False, "step": 0})
    d['logs'].append([datetime.now().strftime('%H:%M'), "전체종료", "청산완료", "정지"])
    save_data(d)
    st.rerun()

# --- 매매 내역 ---
st.subheader("📝 최근 매매 기록")
if d['logs']:
    st.table(pd.DataFrame(d['logs'][::-1], columns=['시간', '작업', '가격', '비고']))
