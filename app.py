
import streamlit as st
import pandas as pd
import ccxt
import json
import os
from datetime import datetime

# --- 데이터 저장 (파일 방식이라 절대 안 날아감) ---
DB = "trade_final.json"
def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"yesu": 10000000, "inv_p": 0, "avg": 0, "run": False, "step": 0, "logs": []}

def save(data):
    with open(DB, "w") as f: json.dump(data, f)

d = load()

# --- 설정 및 시세 ---
st.set_page_config(page_title="코인 8분할 무적 엔진")
st.title("🛡️ 8분할 거미줄 매매 v1.2")

try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
except: price = 0

# --- 수익률 및 자산 정밀 계산 ---
curr_val = (d['inv_p'] / d['avg'] * price) if d['avg'] > 0 else 0
s_geum = curr_val - d['inv_p']
s_rate = (s_geum / d['inv_p'] * 100) if d['inv_p'] > 0 else 0
total = d['yesu'] + curr_val

# --- 상단 전광판 ---
st.metric("🏦 총 자산 (평가금액)", f"{total:,.0f}원")
c1, c2, c3 = st.columns(3)
c1.metric("💵 예수금", f"{d['yesu']:,.0f}원")
c2.metric("📈 수익금", f"{s_geum:,.0f}원")
c3.metric("📊 수익률", f"{s_rate:.2f}%")

st.info(f"현재가: {price:,.0f}원 | 내 평단: {d['avg']:,.0f}원")

# --- 8분할 자동 매수 로직 (언니의 알고리즘) ---
if d['run']:
    # 2차: -4% 하락 시 1차의 115% 매수
    if d['step'] == 1 and s_rate <= -4:
        buy_amt = 1000000 * 1.15
        d['yesu'] -= buy_amt
        d['avg'] = ((d['inv_p'] + buy_amt) / (d['inv_p']/d['avg'] + buy_amt/price))
        d['inv_p'] += buy_amt
        d['step'] = 2
        d['logs'].append([datetime.now().strftime('%H:%M'), "2차 매수", "-4% 하락 물타기"])
        save(d)
        st.rerun()
    
    # 3차: -6% 하락 시 (1+2차) 합계의 2/3 매수
    elif d['step'] == 2 and s_rate <= -6:
        buy_amt = d['inv_p'] * (2/3)
        d['yesu'] -= buy_amt
        d['avg'] = ((d['inv_p'] + buy_amt) / (d['inv_p']/d['avg'] + buy_amt/price))
        d['inv_p'] += buy_amt
        d['step'] = 3
        d['logs'].append([datetime.now().strftime('%H:%M'), "3차 매수", "-6% 하락 물타기"])
        save(d)
        st.rerun()

# --- 제어 버튼 ---
col_st, col_ed = st.columns(2)
if col_st.button("▶️ 1차 매수 시작", use_container_width=True):
    if not d['run']:
        d['run'], d['step'] = True, 1
        amt = 1000000 # 1차 100만원
        d['yesu'] -= amt
        d['inv_p'], d['avg'] = amt, price
        d['logs'].append([datetime.now().strftime('%H:%M'), "1차 매수", "시작"])
        save(d)
        st.rerun()

if col_ed.button("⏹️ 전체 종료 및 매도", use_container_width=True):
    d = {"yesu": total, "inv_p": 0, "avg": 0, "run": False, "step": 0, "logs": []}
    save(d)
    st.rerun()

# --- 기록 기록 ---
st.subheader("📅 매매 로그")
if d['logs']:
    st.table(pd.DataFrame(d['logs'][::-1], columns=['시간', '작업', '내용']))
