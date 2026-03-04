import streamlit as st
import pandas as pd
import ccxt
import json
import os
from datetime import datetime

# 1. 파일 저장 시스템 (새로고침 방어)
DB = "data_v1.json"
def load():
    if os.path.exists(DB):
        with open(DB, "r") as f: return json.load(f)
    return {"yesu": 10000000, "inv_p": 0, "avg": 0, "run": False, "step": 0, "logs": []}

def save(data):
    with open(DB, "w") as f: json.dump(data, f)

d = load()

# 2. 화면 구성
st.set_page_config(page_title="코인 8분할 v1.0")
st.title("💰 8분할 자동매매 엔진")

# 3. 시세 및 자산 계산
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
except:
    price = 0

curr_v = (d['inv_p'] / d['avg'] * price) if d['avg'] > 0 else 0
s_geum = curr_v - d['inv_p']
s_rate = (s_geum / d['inv_p'] * 100) if d['inv_p'] > 0 else 0
total = d['yesu'] + curr_v

# 4. 현황판 (핵심 정보)
st.metric("🏦 총 자산", f"{total:,.0f}원")
c1, c2 = st.columns(2)
c1.metric("💵 예수금", f"{d['yesu']:,.0f}원")
c2.metric("📈 수익금", f"{s_geum:,.0f}원", f"{s_rate:.2f}%")

st.divider()
st.write(f"📍 현재가: **{price:,.0f}원** | 🔵 내 평단: **{d['avg']:,.0f}원**")

# 5. 제어 버튼
b1, b2 = st.columns(2)
if b1.button("▶️ 매매 시작", use_container_width=True):
    if not d['run']:
        d['run'], d['step'] = True, 1
        amt = 1000000 # 1차 100만
        d['yesu'] -= amt
        d['inv_p'], d['avg'] = amt, price
        d['logs'].append([datetime.now().strftime('%H:%M'), "1차매수", f"{price:,.0f}"])
        save(d)
        st.rerun()

if b2.button("⏹️ 전체종료", use_container_width=True):
    d.update({"yesu": total, "inv_p": 0, "avg": 0, "run": False, "step": 0})
    d['logs'].append([datetime.now().strftime('%H:%M'), "전체종료", "청산"])
    save(d)
    st.rerun()

# 6. 기록
st.subheader("📝 매매 기록")
if d['logs']:
    st.table(pd.DataFrame(d['logs'][::-1], columns=['시간', '작업', '가격']))
