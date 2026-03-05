import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
from math import floor
import uuid
import traceback

# =========================
# v41 - 부석 거미줄 시스템
# - 새로고침(브라우저)에도 상태 유지(메모리+uid)
# - 실전 매수 실행(안전장치 포함)
# - 에러 로그 정리
# - 모의(핑크) / 실전(블루) 테마
# =========================

st.set_page_config(page_title="부석 거미줄 v41", layout="wide")

APP_TITLE = "💎 부석 거미줄 v41"
SYMBOL = "BTC/KRW"
N_SPLIT = 8

# -------------------------
# (1) 새로고침에도 유지: 서버 메모리 저장소 + URL uid
# -------------------------
@st.cache_resource
def get_store():
    # 서버 프로세스 메모리. 새로고침해도 대개 유지됨(서버 재시작 제외).
    return {}

def get_uid():
    # Streamlit query params (URL ?uid=xxxx)
    qp = st.query_params
    uid = qp.get("uid", None)
    if not uid:
        uid = str(uuid.uuid4())[:8]
        st.query_params["uid"] = uid
    return uid

UID = get_uid()
STORE = get_store()

def default_state():
    return {
        "mode": "paper",  # paper | live
        "paper": {
            "budget": 10_000_000,
            "krw": 10_000_000,
            "btc": 0.0,
            "avg": 0.0,
            "spent": 0,
            "logs": [],
        },
        "live_logs": [],
        "errors": [],   # 에러 로그 모음
        "mobile_ui": True,
        "live_trade_enabled": False,  # 실전 매수 허용(안전장치)
    }

if UID not in STORE:
    STORE[UID] = default_state()

S = STORE[UID]  # shorthand

def log_error(e: Exception, context: str = ""):
    msg = f"[{datetime.now().strftime('%m/%d %H:%M:%S')}] {context} :: {type(e).__name__}: {e}"
    # 너무 길면 요약 + 상세는 traceback 따로
    tb = traceback.format_exc()
    S["errors"].append({"msg": msg, "traceback": tb})

def clear_errors():
    S["errors"] = []

# -------------------------
# (2) 테마(CSS) - 모의=핑크, 실전=블루
# -------------------------
def apply_theme(mode: str):
    if mode == "paper":
        # Pink theme
        bg1, bg2 = "#2a0f1f", "#120811"
        accent = "#ff4fa7"
        accent2 = "#ff9bd1"
        card = "rgba(255, 79, 167, 0.10)"
        label = "모의투자(핑크)"
    else:
        # Blue theme
        bg1, bg2 = "#071a2a", "#05101a"
        accent = "#2da8ff"
        accent2 = "#7ec8ff"
        card = "rgba(45, 168, 255, 0.10)"
        label = "실전투자(블루)"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: radial-gradient(1200px 600px at 20% 10%, {bg1} 0%, {bg2} 60%);
        }}
        /* 상단 타이틀 느낌 */
        .app-badge {{
            display:inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: {card};
            border: 1px solid rgba(255,255,255,0.08);
            color: {accent2};
            font-weight: 700;
            margin-bottom: 10px;
        }}
        /* 버튼 강조 */
        div.stButton > button {{
            border-radius: 12px;
        }}
        /* expander 헤더 색감 */
        div[data-testid="stExpander"] > details {{
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
        }}
        /* metric 카드 느낌(완벽하진 않지만 분위기) */
        div[data-testid="stMetric"] {{
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.08);
            padding: 12px 14px;
            border-radius: 14px;
        }}
        /* 링크/포인트 컬러 */
        a, code {{
            color: {accent2} !important;
        }}
        </style>
        <div class="app-badge">UID: {UID} · {label}</div>
        """,
        unsafe_allow_html=True
    )

apply_theme(S["mode"])

# -------------------------
# CCXT helpers
# -------------------------
def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def parse_avg_buy_price(info_obj, currency="BTC"):
    # Upbit balance info 예시는 avg_buy_price를 포함 [Source]
    # https://global-docs.upbit.com/docs/ccxt-library-integration-guide
    try:
        if isinstance(info_obj, list):
            for row in info_obj:
                if isinstance(row, dict) and row.get("currency") == currency:
                    return safe_float(row.get("avg_buy_price", 0), 0.0)
        if isinstance(info_obj, dict):
            for key in ["data", "balances", "result", "info"]:
                if key in info_obj:
                    v = info_obj[key]
                    avg = parse_avg_buy_price(v, currency=currency)
                    if avg > 0:
                        return avg
    except:
        pass
    return 0.0

@st.cache_data(ttl=2)
def fetch_price():
    ex = ccxt.upbit({"enableRateLimit": True})
    return float(ex.fetch_ticker(SYMBOL)["last"])

@st.cache_data(ttl=10)
def fetch_ohlcv(timeframe: str, limit: int = 80):
    ex = ccxt.upbit({"enableRateLimit": True})
    ohlcv = ex.fetch_ohlcv(SYMBOL, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["t", "o", "h", "l", "c", "v"])
    df["dt"] = pd.to_datetime(df["t"], unit="ms")
    return df

def upbit_private(access_key: str, secret_key: str):
    ex = ccxt.upbit({
        "apiKey": access_key,
        "secret": secret_key,
        "enableRateLimit": True,
    })
    # Upbit 시장가 매수에서 cost(KRW)로 넣고 싶으면 아래 옵션이 중요
    # 관련 오류/설명: CCXT issue [Source]
    # https://github.com/ccxt/ccxt/issues/9079
    ex.options["createMarketBuyOrderRequiresPrice"] = False
    return ex

def fetch_live_balance(access_key: str, secret_key: str):
    ex = upbit_private(access_key, secret_key)
    bal = ex.fetch_balance()
    krw_free = safe_float(bal.get("KRW", {}).get("free", 0), 0.0)
    btc_total = safe_float(bal.get("BTC", {}).get("total", 0), 0.0)
    avg_buy = parse_avg_buy_price(bal.get("info", None), currency="BTC")
    return krw_free, btc_total, avg_buy

# -------------------------
# 8분할 가중치(1..8)
# -------------------------
def weighted_amount_for_step(budget: int, step: int, n: int = 8):
    step = max(1, min(int(step), int(n)))
    total_w = n * (n + 1) // 2  # 36
    if step < n:
        return int(floor(budget * (step / total_w)))
    prev_sum = 0
    for s in range(1, n):
        prev_sum += int(floor(budget * (s / total_w)))
    return max(0, int(budget - prev_sum))

def fmt_krw(x):
    try:
        return f"{float(x):,.0f}원"
    except:
        return "0원"

def fmt_pct(x):
    try:
        return f"{float(x):.2f}%"
    except:
        return "0.00%"

# -------------------------
# UI: Header
# -------------------------
st.title(APP_TITLE)

# 모드 버튼 (브라우저 새로고침해도 STORE에 저장되므로 유지)
c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
with c1:
    if st.button("🌸 모의투자", use_container_width=True, type=("primary" if S["mode"]=="paper" else "secondary")):
        S["mode"] = "paper"
        clear_errors()
        st.rerun()
with c2:
    if st.button("🚀 실전투자", use_container_width=True, type=("primary" if S["mode"]=="live" else "secondary")):
        S["mode"] = "live"
        clear_errors()
        st.rerun()
with c3:
    st.caption("브라우저 새로고침(F5/당겨서)해도 UID 기준으로 상태를 다시 불러옵니다.\n(단, 서버가 완전 재시작되면 초기화될 수 있어요)")

# -------------------------
# 설정(사이드바 + 본문 Expander)
# -------------------------
def settings_panel(prefix: str):
    st.subheader("⚙️ 설정")

    S["mobile_ui"] = st.toggle("📱 모바일 UI(분봉 selectbox)", value=S["mobile_ui"], key=f"{prefix}_mobile")

    budget = st.number_input(
        "모의 예산(초기/리셋 기준)",
        min_value=1_000_000,
        max_value=500_000_000,
        step=500_000,
        value=int(S["paper"]["budget"]),
        key=f"{prefix}_budget",
    )

    acc = st.text_input("Upbit Access Key", type="password", key=f"{prefix}_acc")
    sec = st.text_input("Upbit Secret Key", type="password", key=f"{prefix}_sec")

    if st.button("💾 모의 예산 적용(모의계정 초기화)", use_container_width=True, key=f"{prefix}_apply"):
        S["paper"] = {
            "budget": int(budget),
            "krw": int(budget),
            "btc": 0.0,
            "avg": 0.0,
            "spent": 0,
            "logs": [],
        }
        st.success("모의 예산 적용 + 초기화 완료")
        st.rerun()

    # "새로고침 버튼 제거" 요청: 앱 내부 새로고침 버튼은 두지 않음.
    # 대신 초기화만 제공
    if st.button("🧹 데이터 초기화(모의/로그)", use_container_width=True, key=f"{prefix}_reset"):
        b = int(S["paper"]["budget"])
        S["paper"] = {"budget": b, "krw": b, "btc": 0.0, "avg": 0.0, "spent": 0, "logs": []}
        S["live_logs"] = []
        clear_errors()
        st.success("초기화 완료")
        st.rerun()

    return acc, sec

with st.expander("🔑 업비트 API 설정 (연결 후 접어두세요)", expanded=False):
    acc_main, sec_main = settings_panel("main")

with st.sidebar:
    st.header("📌 사이드바(폴드에서 메뉴로 숨겨질 수 있어요)")
    acc_side, sec_side = settings_panel("side")

ACCESS_KEY = acc_main or acc_side
SECRET_KEY = sec_main or sec_side

# -------------------------
# 데이터 계산
# -------------------------
try:
    price = fetch_price()
except Exception as e:
    log_error(e, "시세 조회 실패")
    st.error("📡 시세 연결 실패. 잠시 후 다시 시도해주세요.")
    st.stop()

# 모드별 지표
if S["mode"] == "paper":
    p = S["paper"]
    krw_cash = float(p["krw"])
    btc_qty = float(p["btc"])
    avg_buy = float(p["avg"])
    cost_basis = float(p["spent"])
else:
    if ACCESS_KEY and SECRET_KEY:
        try:
            krw_cash, btc_qty, avg_buy = fetch_live_balance(ACCESS_KEY, SECRET_KEY)
        except Exception as e:
            log_error(e, "실전 잔고 조회 실패")
            krw_cash, btc_qty, avg_buy = 0.0, 0.0, 0.0
    else:
        krw_cash, btc_qty, avg_buy = 0.0, 0.0, 0.0

    cost_basis = (btc_qty * avg_buy) if (btc_qty > 0 and avg_buy > 0) else 0.0

market_value = btc_qty * price
total_asset = krw_cash + market_value
pnl = market_value - cost_basis
roi = (pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

# -------------------------
# Metrics
# -------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("🏦 총자산(현금+코인)", fmt_krw(total_asset))
m2.metric("💵 현금", fmt_krw(krw_cash))
m3.metric("📈 수익률", fmt_pct(roi))
m4.metric("🎯 평단", fmt_krw(avg_buy) if avg_buy > 0 else "—")

d1, d2, d3 = st.columns(3)
d1.metric("🧾 매수원금(원금)", fmt_krw(cost_basis))
d2.metric("💹 코인평가금", fmt_krw(market_value))
d3.metric("🟢 손익", fmt_krw(pnl))

st.divider()

# -------------------------
# 매수 실행
# -------------------------
if S["mode"] == "paper":
    done = len(S["paper"]["logs"])
    step = min(done + 1, N_SPLIT)
    budget = int(S["paper"]["budget"])
    amount = weighted_amount_for_step(budget, step, n=N_SPLIT)

    st.caption(f"8분할 가중치(1..8) 추천: **{step}차 = {amount:,.0f}원** / 예산 {budget:,.0f}원")

    if st.button(f"🔥 {step}차 모의 매수 ({amount:,.0f}원)", use_container_width=True, type="primary", disabled=(amount <= 0 or step > N_SPLIT)):
        try:
            p = S["paper"]
            if p["krw"] < amount:
                st.warning("모의 현금이 부족합니다.")
            else:
                btc_bought = amount / price
                new_btc = p["btc"] + btc_bought
                new_spent = p["spent"] + int(amount)
                new_avg = (new_spent / new_btc) if new_btc > 0 else 0.0

                p["krw"] -= int(amount)
                p["btc"] = float(new_btc)
                p["spent"] = int(new_spent)
                p["avg"] = float(new_avg)

                p["logs"].append({
                    "시간": datetime.now().strftime("%m/%d %H:%M:%S"),
                    "모드": "모의",
                    "차수": step,
                    "매수금액(KRW)": int(amount),
                    "체결가": float(price),
                    "매수수량(BTC)": float(btc_bought),
                    "평단(갱신)": float(new_avg),
                })
                clear_errors()
                st.success("모의 매수(기록) 완료")
                st.rerun()
        except Exception as e:
            log_error(e, "모의 매수 처리 실패")
            st.error("모의 매수 처리 중 오류가 발생했습니다. 아래 에러 로그를 확인하세요.")

else:
    # 실전 매수 활성화 스위치 + 확인문구(안전장치)
    left, right = st.columns([1.2, 1])
    with left:
        S["live_trade_enabled"] = st.toggle("⚠️ 실전 매수 실행 허용", value=S["live_trade_enabled"])
    with right:
        confirm_text = st.text_input("확인문구 입력: '매수' 입력해야 실행", value="", placeholder="매수")

    done = len(S["live_logs"])
    step = min(done + 1, N_SPLIT)

    # 실전에서는 기준 예산은 모의 budget을 전략 기준으로 사용
    strategy_budget = int(S["paper"]["budget"])
    amount = weighted_amount_for_step(strategy_budget, step, n=N_SPLIT)

    st.caption(f"실전 8분할 가중치 추천: **{step}차 = {amount:,.0f}원** (전략예산 {strategy_budget:,.0f} 기준)")

    can_trade = bool(ACCESS_KEY and SECRET_KEY and S["live_trade_enabled"] and (confirm_text.strip() == "매수"))
    btn = st.button(f"🚀 {step}차 실전 시장가 매수 실행 ({amount:,.0f}원)", use_container_width=True, type="primary", disabled=not can_trade)

    if btn:
        try:
            ex = upbit_private(ACCESS_KEY, SECRET_KEY)

            # 잔고 체크(부족하면 중단)
            krw_free, _, _ = fetch_live_balance(ACCESS_KEY, SECRET_KEY)
            if krw_free < amount:
                st.warning(f"KRW 잔고 부족: 보유 {krw_free:,.0f}원 / 필요 {amount:,.0f}원")
            else:
                # 핵심: Upbit + CCXT 옵션으로 KRW cost를 amount로 넣는 방식
                order = ex.create_market_buy_order(SYMBOL, amount)

                S["live_logs"].append({
                    "시간": datetime.now().strftime("%m/%d %H:%M:%S"),
                    "모드": "실전",
                    "차수": step,
                    "매수금액(KRW)": int(amount),
                    "주문결과": str(order)[:500],  # 너무 길어질 수 있어 500자로 제한
                })
                clear_errors()
                st.success("실전 주문 요청 완료! (업비트 체결은 앱/웹에서 확인)")
                st.rerun()

        except Exception as e:
            log_error(e, "실전 매수 실행 실패")
            st.error("실전 매수 중 오류가 발생했습니다. 아래 에러 로그를 확인하세요.")

st.divider()

# -------------------------
# Tabs
# -------------------------
t1, t2, t3, t4 = st.tabs(["📋 매수 기록", "📈 비트코인 차트", "📊 요약", "🧯 에러 로그"])

with t1:
    if S["mode"] == "paper":
        logs = S["paper"]["logs"]
    else:
        logs = S["live_logs"]
    if logs:
        st.dataframe(pd.DataFrame(logs)[::-1], use_container_width=True, hide_index=True)
    else:
        st.write("아직 기록이 없습니다.")

with t2:
    timeframes = ["1m", "5m", "30m", "1h"]
    if S["mobile_ui"]:
        tf = st.selectbox("분봉", timeframes, index=2)
    else:
        tf = st.radio("분봉", timeframes, index=2, horizontal=True)

    try:
        df = fetch_ohlcv(tf, limit=80)
        fig = go.Figure(data=[
            go.Candlestick(
                x=df["dt"], open=df["o"], high=df["h"], low=df["l"], close=df["c"], name="BTC/KRW"
            )
        ])
        if avg_buy and avg_buy > 0:
            fig.add_hline(y=avg_buy, line_dash="dash", line_color="yellow", annotation_text="평단")
        fig.add_hline(y=price, line_dash="dot", line_color="#7ec8ff", annotation_text="현재가")
        fig.update_layout(template="plotly_dark", height=420, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        log_error(e, "차트 조회 실패")
        st.warning("차트 데이터를 불러오지 못했습니다. 에러 로그를 확인하세요.")

with t3:
    st.write(pd.DataFrame([{
        "모드": "모의(핑크)" if S["mode"]=="paper" else "실전(블루)",
        "현재가": price,
        "BTC 수량": btc_qty,
        "평단": avg_buy,
        "원금": cost_basis,
        "평가": market_value,
        "손익": pnl,
        "수익률(%)": roi,
    }]))

with t4:
    if not S["errors"]:
        st.success("현재 에러 없음")
    else:
        st.warning(f"에러 {len(S['errors'])}건")
        for i, item in enumerate(S["errors"][::-1][:10], start=1):
            with st.expander(f"에러 #{i}: {item['msg']}", expanded=False):
                st.code(item["traceback"])

st.caption("참고: Upbit 잔고 응답에 avg_buy_price가 포함된 예시는 Upbit CCXT 가이드에 있습니다. [Source](https://global-docs.upbit.com/docs/ccxt-library-integration-guide)")
st.caption("참고: Upbit 시장가 매수에서 CCXT 옵션(createMarketBuyOrderRequiresPrice) 관련 오류/설명은 CCXT 이슈에 정리돼 있습니다. [Source](https://github.com/ccxt/ccxt/issues/9079)")
