import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
from math import floor
import uuid
import traceback

# =========================================================
# 부석 거미줄 v41
# 1) 모바일 웹 새로고침에도 "최대한" 초기화 안되게 (UID + 서버 메모리 저장)
# 2) 실전 투자: 실제 시장가 매수 지원 (안전장치 2중)
# 3) 조회/차트 에러는 화면 도배 대신 "에러 로그 탭"에 모아서 표시
# 4) 모의=핑크 테마 / 실전=블루 테마 (CSS)
#
# 주의:
# - "브라우저 새로고침"은 Streamlit 세션이 바뀔 수 있어 session_state는 날아갈 수 있음
#   → 그래서 서버 메모리 STORE(캐시 리소스) + URL uid로 복구하도록 구현
# - 서버가 재시작(배포/슬립/리부트)되면 STORE는 초기화될 수 있음
#   (영구 저장까지 원하면 JSON/DB 저장으로 v42에서 확장 가능)
# =========================================================

APP_TITLE = "💎 부석 거미줄 v41"
SYMBOL = "BTC/KRW"
N_SPLIT = 8
MIN_ORDER_KRW = 5000  # 업비트 최소 주문금액(보수적으로 5,000원 기준)

st.set_page_config(page_title="부석 거미줄 v41", layout="wide")

# -------------------------
# URL uid + 서버 메모리 STORE
# -------------------------
@st.cache_resource
def get_store():
    # 서버 메모리(프로세스) 저장소
    return {}

def get_query_params():
    # streamlit 버전 호환용
    try:
        return dict(st.query_params)
    except Exception:
        try:
            return st.experimental_get_query_params()
        except Exception:
            return {}

def set_query_param(uid: str):
    try:
        st.query_params["uid"] = uid
    except Exception:
        st.experimental_set_query_params(uid=uid)

def get_uid():
    qp = get_query_params()
    uid = None
    if "uid" in qp:
        v = qp["uid"]
        uid = v[0] if isinstance(v, list) else v
    if not uid:
        uid = str(uuid.uuid4())[:8]
        set_query_param(uid)
    return uid

UID = get_uid()
STORE = get_store()

def default_state():
    return {
        "mode": "paper",  # paper | live
        "mobile_ui": True,
        "paper": {
            "budget": 10_000_000,
            "krw": 10_000_000,
            "btc": 0.0,
            "avg": 0.0,
            "spent": 0,   # 누적 매수 원금(원화)
            "logs": [],
        },
        "live_logs": [],
        "errors": [],  # {"time":..., "context":..., "msg":..., "tb":...}
    }

if UID not in STORE:
    STORE[UID] = default_state()

S = STORE[UID]

def now_str():
    return datetime.now().strftime("%m/%d %H:%M:%S")

def push_error(e: Exception, context: str):
    S["errors"].append({
        "time": now_str(),
        "context": context,
        "msg": f"{type(e).__name__}: {e}",
        "tb": traceback.format_exc()
    })

def clear_errors():
    S["errors"] = []

# -------------------------
# 테마(CSS): 모의=핑크 / 실전=블루
# -------------------------
def apply_theme(mode: str, uid: str):
    if mode == "paper":
        # pink
        bg1, bg2 = "#2a0f1f", "#120811"
        accent = "#ff4fa7"
        accent2 = "#ff9bd1"
        badge = "모의투자(핑크)"
        card = "rgba(255, 79, 167, 0.12)"
    else:
        # blue
        bg1, bg2 = "#071a2a", "#05101a"
        accent = "#2da8ff"
        accent2 = "#7ec8ff"
        badge = "실전투자(블루)"
        card = "rgba(45, 168, 255, 0.12)"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: radial-gradient(1200px 650px at 20% 10%, {bg1} 0%, {bg2} 65%);
        }}
        .badge {{
            display:inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: {card};
            border: 1px solid rgba(255,255,255,0.10);
            color: {accent2};
            font-weight: 800;
            margin: 2px 0 10px 0;
        }}
        div[data-testid="stMetric"] {{
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.08);
            padding: 12px 14px;
            border-radius: 14px;
        }}
        div[data-testid="stExpander"] > details {{
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
        }}
        a, code {{
            color: {accent2} !important;
        }}
        </style>
        <div class="badge">UID: {uid} · {badge}</div>
        """,
        unsafe_allow_html=True
    )

apply_theme(S["mode"], UID)

# -------------------------
# CCXT / Upbit helpers
# -------------------------
def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def parse_avg_buy_price(info_obj, currency="BTC"):
    """
    Upbit CCXT 가이드의 예시에서 balance['info']는 리스트이며 avg_buy_price가 포함됨. [Source]
    https://global-docs.upbit.com/docs/ccxt-library-integration-guide
    """
    try:
        if isinstance(info_obj, list):
            for row in info_obj:
                if isinstance(row, dict) and row.get("currency") == currency:
                    return safe_float(row.get("avg_buy_price", 0), 0.0)
        if isinstance(info_obj, dict):
            for key in ["data", "balances", "result", "info"]:
                if key in info_obj:
                    v = info_obj[key]
                    got = parse_avg_buy_price(v, currency=currency)
                    if got > 0:
                        return got
    except Exception:
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

    # 핵심 옵션: Upbit 시장가 매수에서 price를 요구하는 오류가 발생할 수 있어
    # amount를 "KRW cost"로 넣을 수 있게 옵션을 False로 (대표 이슈) [Source]
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

def place_market_buy_upbit(ex, symbol: str, krw_cost: int):
    """
    Upbit 시장가 매수 실행.
    CCXT/버전별로 동작이 달라질 수 있어 여러 방식으로 순차 시도.
    """
    last_err = None

    # 1) 옵션 False 상태에서 create_market_buy_order(symbol, cost) 시도
    try:
        return ex.create_market_buy_order(symbol, krw_cost)
    except Exception as e:
        last_err = e

    # 2) create_market_buy_order_with_cost 가 있으면 시도(일부 거래소/버전에서 제공)
    try:
        fn = getattr(ex, "create_market_buy_order_with_cost", None)
        if callable(fn):
            return fn(symbol, krw_cost)
    except Exception as e:
        last_err = e

    # 3) create_order + cost 파라미터 시도 (거래소별 params를 쓰는 경우)
    try:
        return ex.create_order(symbol, "market", "buy", krw_cost, None, {"cost": krw_cost})
    except Exception as e:
        last_err = e

    raise last_err

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
    except Exception:
        return "0원"

def fmt_pct(x):
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return "0.00%"

# =========================================================
# UI
# =========================================================
st.title(APP_TITLE)

# 상단 모드 버튼(앱 내부 '새로고침 버튼'은 제거 요청대로 없음)
c1, c2, c3 = st.columns([1.2, 1.2, 2.2])
with c1:
    if st.button("🌸 모의투자", use_container_width=True, type=("primary" if S["mode"] == "paper" else "secondary")):
        S["mode"] = "paper"
        clear_errors()
        st.rerun()
with c2:
    if st.button("🚀 실전투자", use_container_width=True, type=("primary" if S["mode"] == "live" else "secondary")):
        S["mode"] = "live"
        clear_errors()
        st.rerun()
with c3:
    st.caption(
        "핸드폰 웹 새로고침(당겨서 새로고침)해도 UID 기준으로 상태를 복구하도록 설계.\n"
        "단, 서버가 재시작되면(배포/리부트/슬립) 메모리는 초기화될 수 있어요."
    )

# -------------------------
# 설정 패널(본문 expander + sidebar 이중 제공)
# -------------------------
def settings_panel(prefix: str):
    st.subheader("⚙️ 설정")

    mobile_ui = st.toggle("📱 모바일 UI(분봉 selectbox)", value=S.get("mobile_ui", True), key=f"{prefix}_mobile")
    S["mobile_ui"] = bool(mobile_ui)

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

    colA, colB = st.columns(2)
    with colA:
        if st.button("💾 모의 예산 적용(모의계정 초기화)", use_container_width=True, key=f"{prefix}_apply"):
            S["paper"] = {
                "budget": int(budget),
                "krw": int(budget),
                "btc": 0.0,
                "avg": 0.0,
                "spent": 0,
                "logs": [],
            }
            clear_errors()
            st.success("모의 예산 적용 + 초기화 완료")
            st.rerun()
    with colB:
        if st.button("🧹 데이터 초기화(모의/실전로그)", use_container_width=True, key=f"{prefix}_reset"):
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

# =========================================================
# 데이터 계산(공통)
# =========================================================
try:
    price = fetch_price()
except Exception as e:
    push_error(e, "시세 조회 실패")
    st.error("📡 시세 연결 실패. 에러 로그 탭을 확인하세요.")
    st.stop()

# 모드별 계정 상태
if S["mode"] == "paper":
    p = S["paper"]
    krw_cash = float(p["krw"])
    btc_qty = float(p["btc"])
    avg_buy = float(p["avg"])
    cost_basis = float(p["spent"])
else:
    krw_cash, btc_qty, avg_buy = 0.0, 0.0, 0.0
    if ACCESS_KEY and SECRET_KEY:
        try:
            krw_cash, btc_qty, avg_buy = fetch_live_balance(ACCESS_KEY, SECRET_KEY)
        except Exception as e:
            push_error(e, "실전 잔고 조회 실패")
    cost_basis = (btc_qty * avg_buy) if (btc_qty > 0 and avg_buy > 0) else 0.0

market_value = btc_qty * price
total_asset = krw_cash + market_value
pnl = market_value - cost_basis
roi = (pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

# =========================================================
# 메트릭
# =========================================================
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

# =========================================================
# 매수 실행(모의/실전)
# =========================================================
if S["mode"] == "paper":
    done = len(S["paper"]["logs"])
    step = min(done + 1, N_SPLIT)
    budget = int(S["paper"]["budget"])
    amount = weighted_amount_for_step(budget, step, n=N_SPLIT)

    st.caption(f"8분할 가중치(1..8) 추천: **{step}차 = {amount:,.0f}원** / 예산 {budget:,.0f}원")

    if st.button(
        f"🔥 {step}차 모의 매수 ({amount:,.0f}원)",
        use_container_width=True,
        type="primary",
        disabled=(amount <= 0 or step > N_SPLIT or amount < MIN_ORDER_KRW),
    ):
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
                    "시간": now_str(),
                    "모드": "모의",
                    "차수": step,
                    "매수금액(KRW)": int(amount),
                    "기준가(현재가)": float(price),
                    "매수수량(BTC)": float(btc_bought),
                    "평단(갱신)": float(new_avg),
                })
                clear_errors()
                st.success("모의 매수(기록) 완료")
                st.rerun()
        except Exception as e:
            push_error(e, "모의 매수 처리 실패")
            st.error("모의 매수 처리 중 오류가 발생했습니다. 에러 로그 탭을 확인하세요.")

else:
    st.subheader("🚀 실전 매수 (주의: 실제 주문 나갑니다)")

    warn = (
        "실전 매수는 실제 주문이 나갑니다.\n\n"
        "안전장치:\n"
        "1) '실전매수 허용' 토글 ON\n"
        "2) 확인문구에 '매수' 정확히 입력\n"
    )
    st.info(warn)

    colL, colR = st.columns([1.2, 1.0])
    with colL:
        live_trade_enabled = st.toggle("⚠️ 실전매수 허용", value=False, key="live_trade_enabled")
    with colR:
        confirm = st.text_input("확인문구(매수)", value="", placeholder="매수", key="live_trade_confirm")

    done = len(S["live_logs"])
    step = min(done + 1, N_SPLIT)
    strategy_budget = int(S["paper"]["budget"])
    amount = weighted_amount_for_step(strategy_budget, step, n=N_SPLIT)

    st.caption(f"실전 8분할 가중치 추천: **{step}차 = {amount:,.0f}원** (전략예산 {strategy_budget:,.0f} 기준)")

    can_trade = bool(
        ACCESS_KEY and SECRET_KEY and live_trade_enabled and (confirm.strip() == "매수") and amount >= MIN_ORDER_KRW
    )

    if st.button(
        f"🚀 {step}차 실전 시장가 매수 실행 ({amount:,.0f}원)",
        use_container_width=True,
        type="primary",
        disabled=not can_trade,
    ):
        try:
            ex = upbit_private(ACCESS_KEY, SECRET_KEY)

            # 주문 직전 잔고 재확인
            krw_free, _, _ = fetch_live_balance(ACCESS_KEY, SECRET_KEY)
            if krw_free < amount:
                st.warning(f"KRW 잔고 부족: 보유 {krw_free:,.0f}원 / 필요 {amount:,.0f}원")
            else:
                order = place_market_buy_upbit(ex, SYMBOL, int(amount))

                S["live_logs"].append({
                    "시간": now_str(),
                    "모드": "실전",
                    "차수": step,
                    "매수금액(KRW)": int(amount),
                    "주문요청": "시장가 매수",
                    "결과요약": str(order)[:600],
                })
                clear_errors()
                st.success("실전 주문 요청 완료! 업비트 체결/내역은 업비트 앱에서 확인하세요.")
                st.rerun()

        except Exception as e:
            push_error(e, "실전 시장가 매수 실패")
            st.error("실전 매수 중 오류가 발생했습니다. 에러 로그 탭을 확인하세요.")

st.divider()

# =========================================================
# Tabs: 기록 / 차트 / 요약 / 에러 로그
# =========================================================
tab1, tab2, tab3, tab4 = st.tabs(["📋 기록", "📈 차트", "📊 요약", "🧯 에러 로그"])

with tab1:
    if S["mode"] == "paper":
        logs = S["paper"]["logs"]
    else:
        logs = S["live_logs"]

    if logs:
        st.dataframe(pd.DataFrame(logs)[::-1], use_container_width=True, hide_index=True)
    else:
        st.write("아직 기록이 없습니다.")

with tab2:
    timeframes = ["1m", "5m", "30m", "1h"]
    if S.get("mobile_ui", True):
        tf = st.selectbox("분봉", timeframes, index=2)
    else:
        tf = st.radio("분봉", timeframes, index=2, horizontal=True)

    try:
        df = fetch_ohlcv(tf, limit=80)
        fig = go.Figure(data=[
            go.Candlestick(
                x=df["dt"],
                open=df["o"], high=df["h"], low=df["l"], close=df["c"],
                name="BTC/KRW"
            )
        ])
        if avg_buy and avg_buy > 0:
            fig.add_hline(y=avg_buy, line_dash="dash", line_color="yellow", annotation_text="평단")
        fig.add_hline(y=price, line_dash="dot", line_color="#7ec8ff", annotation_text="현재가")
        fig.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        push_error(e, "차트 로딩 실패")
        st.warning("차트 데이터를 불러오지 못했습니다. 에러 로그 탭을 확인하세요.")

with tab3:
    st.dataframe(pd.DataFrame([{
        "UID": UID,
        "모드": "모의(핑크)" if S["mode"] == "paper" else "실전(블루)",
        "현재가": price,
        "BTC 수량": btc_qty,
        "평단": avg_buy,
        "원금": cost_basis,
        "평가": market_value,
        "손익": pnl,
        "수익률(%)": roi,
    }]), use_container_width=True, hide_index=True)

with tab4:
    if not S["errors"]:
        st.success("현재 에러 없음")
    else:
        st.warning(f"에러 {len(S['errors'])}건 (최근 10개만 표시)")
        for i, err in enumerate(S["errors"][::-1][:10], start=1):
            title = f"#{i} · {err['time']} · {err['context']} · {err['msg']}"
            with st.expander(title, expanded=False):
                st.code(err["tb"])

st.caption("Upbit CCXT 잔고 예시( avg_buy_price 포함 )는 공식 가이드에 있습니다. [Source](https://global-docs.upbit.com/docs/ccxt-library-integration-guide)")
st.caption("Upbit 시장가 매수 시 CCXT 옵션/오류 관련 대표 이슈입니다. [Source](https://github.com/ccxt/ccxt/issues/9079)")
