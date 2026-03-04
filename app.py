import streamlit as st
import pandas as pd
import ccxt
import requests
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import os

# --- 1. 저장 시스템 (새로고침해도 내 돈 기록 안날아가게!) ---
DB_FILE = "trading_data_final.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {"yesu": 10000000, "inv_p": 0, "avg": 0, "logs": []}

def save_data(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f)

# 데이터 초기 로드
if 'mock_data' not in st.session_state:
    st.session_state.mock_data = load_data()

# --- 2. IP 주소 확인 (업비트 등록용) ---
def get_ip():
    try: return requests.get("https://api64.ipify.org", timeout=3).text
    except: return "IP 확인 중..."

# --- 3. 페이지 설정 및 테마 ---
st.set_page_config(page_title="거미줄 v23 최종", layout="wide")
theme_color = "#3498db" if st.session_state.get('is_real', False) else "#ff69b4"

st.markdown(f"""
    <style>
    .stApp {{ border-top: 15px solid {theme_color}; background-color: #0e1117; }}
    .ip-box {{ background: #1e293b; padding: 15px; border-radius: 10px; border: 2px solid {theme_color}; text-align: center; }}
    .metric-v {{ color: {theme_color} !important; font-size: 2rem; font-weight: bold; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. [최상단] IP 안내 및 모드 전환 ---
my_ip = get_ip()
st.markdown(f'<div class="ip-box">📍 업비트 등록용 IP: <b style="font-size:1.5rem;">{my_ip}</b></div>', unsafe_allow_html=True)
st.caption("※ 위 숫자를 업비트 API 관리에서 쉼표(,) 찍고 추가하세요!")

st.title("💎 부석 거미줄 시스템 v23")

c1, c2 = st.columns(2)
with c1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type="primary" if not st.session_state.get('is_real', False) else "secondary"):
        st.session_state.is_real = False; st.rerun()
with c2:
    if st.button("🚀 실전투자 모드", use_container_width=True, type="primary" if st.session_state.get('is_real', False) else "secondary"):
        st.session_state.is_real = True; st.rer
