import streamlit as st
import pandas as pd
import ccxt
import json
import os
from datetime import datetime

# 1. 파일 저장/불러오기 함수
DB_FILE = "data.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"balance": 10000000, "logs": [], "run": False}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# 2. 데이터 불러오기
saved_data = load_data()

# 3. 화면 설정
st.set_page_config(page_title="코인 8분할 v0.6")
st.title("🟢 비트코인 8분할 매매")

# 4. 현재 상태 표시
st.metric("현재 자산", f"{saved_data['balance']:,.0f}원")

# 5. 가동 버튼 (누르면 상태 저장)
if st.button("▶️ 자동매매 시작", use_container_width=True):
    saved_data['run'] = True
    now = datetime.now().strftime('%H:%M:%S')
    saved_data['logs'].append([now, "BTC", "감시시작", "정상연동", "0%"])
    save_data(saved_data)
    st.success("엔진 가동! (이제 새로고침 해도 유지됩니다)")

if st.button("🔄 기록 초기화 (처음부터 다시)", use_container_width=True):
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    st.rerun()

# 6. 실시간 시세
st.divider()
try:
    upbit = ccxt.upbit()
    price = upbit.fetch_ticker('BTC/KRW')['last']
    st.metric("실시간 BTC 가격", f"{price:,.0f} KRW")
except:
    st.write("시세 로딩 중...")

# 7. 매매 기록 표시
st.subheader("📅 최근 기록")
if saved_data['logs']:
    df = pd.DataFrame(saved_data['logs'], columns=['시간', '종목', '구분', '상태', '수익'])
    st.table(df)
else:
    st.write("시작 버튼을 눌러주세요.")
