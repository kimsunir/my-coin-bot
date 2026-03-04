import streamlit as st
import pandas as pd
import ccxt
import json
import os
from datetime import datetime

# 1. 파일 저장/불러오기
DB_FILE = "trade_v11.json"
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"balance": 10000000, "invested": 0, "avg_price": 0, "logs": [], "run": False, "step": 0}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

d = load_data()

# 2. 화면 설정
st.set_page_config(page_title="코인 8분할 엔진 v1.1")
st.title("🚀 8분할 거미줄 자동매매")

# 3. 실시간 시세 조회
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
except:
    price = 0

# 4. 수익률 및 자산 계산
profit_rate = 0
if d['avg_price'] > 0:
    profit_rate = ((price - d['avg_price']) / d['avg_price']) * 100
total_asset = d['balance'] + (d['invested'] * (1 + profit_rate/100))

# 5. 대시보드
c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{total_asset:,.0f}원")
c2.metric("예수금", f"{d['balance']:,.0f}원")
c3.metric("수익률", f"{profit_rate:.2f}%")

# 6. 버튼
col1, col2 = st.columns(2)
if col1.button("▶️ 자동매매 시작", use_container_width=True):
    if not d['run']:
        d['run'], d['step'] = True, 1
        buy_amt = 1000000
        d['balance'] -= buy_amt
        d['invested'] = buy_amt
        d['avg_price'] = price
        d['logs'].append([datetime.now().strftime('%H:%M'), "1차 매수", f"{price:,.0f}", "시작"])
        save_data(d)
        st.rerun()

if col2.button("⏹️ 종료 및 전액매도", use_container_width=True):
    d = {"balance": total_asset, "invested": 0, "avg_price": 0, "logs": [], "run": False, "step": 0}
    save_data(d)
    st.rerun()

# 7. 매매 기록
st.subheader("📝 매매 기록")
if d['logs']:
    st.table(pd.DataFrame(d['logs'][::-1], columns=['시간', '작업', '내용', '결과']))
