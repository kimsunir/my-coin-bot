import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
from math import floor
import uuid
import traceback
import requests
import time

# =========================================================
# 부석 거미줄 v42 (요청반영 최종)
# - 최상단 Outbound IP 항상 표시(변경 감지)
# - 키 2세트(A/B) 지원 + A 실패 시 B 자동 재시도
# - 사용자 PIN(비번) 맞아야 실전 매매 기능 활성화
# - 업비트 투자정보(평단/원금/평가/손익) 표시
# - 봇 여러회차 누적 매수금액(합산) 별도 표시(모의/실전 각각)
# =========================================================

APP_TITLE = "💎 부석 거미줄 v42"
SYMBOL = "BTC/KRW"
N_SPLIT = 8
MIN_ORDER_KRW = 5000

st.set_page_config(page_title=APP_TITLE, layout="wide")

# -------------------------
# (0) 최상단 Outbound IP 표시
# -------------------------
@st.cache_data(ttl=60)
def get_outbound_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=3).text.strip()
    except Exception:
        return requests.get("https://ifconfig.me/ip", timeout=3).text.strip()

def show_outbound_ip_top():
    try:
        ip = get_outbound_ip()
        prev = st.session_state.get("last_outbound_ip")
        st.info(f"🌐 현재 Outbound IP(업비트 허용 IP에 등록할 값): **{ip}**")
        if prev and prev != ip:
            st.warning(f"⚠️ Outbound IP 변경 감지: {prev} → {ip}")
        st.session_state["last_outbound_ip"] = ip
        return ip
    except Exception as e:
        st.warning(f"🌐 Outbound IP 조회 실패: {e}")
        return None

CURRENT_OUTBOUND_IP = show_outbound_ip_top()

# -------------------------
# (1) 새로고침에도 최대한 유지: URL uid + 서버 메모리 STORE
# -------------------------
@st.cache_resource
def get_store():
    return {}

def get_query_params():
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
            "spent": 0,   # 모의 봇 누적매수합
            "logs": [],
        },
        "live": {
            "spent": 0,   # 실전 봇 누적매수합(요청)
            "logs": [],
        },
        "errors": [],
        "pin_ok": False,
        "pin_fail": 0,
        "pin_lock_until": 0.0,
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
        "tb": traceback.format_exc(),
    })

def clear_errors():
    S["errors"] = []

# -------------------------
# (2) 테마(모의=핑크 / 실전=블루)
# -------------------------
def apply_theme(mode: str, uid: str):
    if mode == "paper":
        bg1, bg2 = "#2a0f1f", "#120811"
        accent2 = "#ff9bd1"
        badge = "모의투자(핑크)"
        card = "rgba(255, 79, 167, 0.12)"
    else:
        bg1, bg2 = "#071a2a", "#05101a"
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
        </style>
        <div class="badge">UID: {uid} · {badge} · Outbound IP: {CURRENT_OUTBOUND_IP}</div>
        """,
        unsafe_allow_html=True
    )

apply_theme(S["mode"], UID)

# -------------------------
# (3) 키 2세트 로딩(입력 우선, 비면 Secrets 사용)
# -------------------------
def get_secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""

def normalize(s: str) -> str:
    return (s or "").strip()

def build_keysets(accA, secA, accB, secB):
    # 입력값이 비면 secrets에서 채움
    accA = normalize(accA) or get_secret("UPBIT_ACCESS_KEY_A")
    secA = normalize(secA) or get_secret("UPBIT_SECRET_KEY_A")
    accB = normalize(accB) or get_secret("UPBIT_ACCESS_KEY_B")
    secB = normalize(secB) or get_secret("UPBIT_SECRET_KEY_B")

    keysets = []
    if accA and secA:
        keysets.append(("A", accA, secA))
    if accB and secB:
        keysets.append(("B", accB, secB))
    return keysets

# -------------------------
# (4) CCXT/Upbit helpers
# -------------------------
def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def parse_avg_buy_price(info_obj, currency="BTC"):
    try:
        if isinstance(info_obj, list):
            for row in info_obj:
                if isinstance(row, dict) and row.get("currency") == currency:
                    return safe_float(row.get("avg_buy_price", 0), 0.0)
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
        "apiKey": access_key.strip(),
        "secret": secret_key.strip(),
        "enableRateLimit": True,
    })
    # Upbit 시장가 매수: cost(KRW)를 amount로 넣는 방식 대응(환경에 따라 다를 수 있음)
    ex.options["createMarketBuyOrderRequiresPrice"] = False
    return ex

def is_retryable_auth_error(e: Exception) -> bool:
    s = str(e)
    # 업비트 REST 에러코드/메시지가 ccxt 예외 문자열에 포함되는 경우가 많음
    retry_keys = [
        "no_authorization_ip",   # IP 미허용
        "invalid_access_key",    # 키 문제
        "expired_access_key",    # 키 만료
        "jwt_verification",      # 인증 실패
        "out_of_scope",          # 권한 부족
    ]
    return any(k in s for k in retry_keys)

def fetch_live_balance_with_fallback(keysets):
    last_err = None
    for label, acc, sec in keysets:
        try:
            ex = upbit_private(acc, sec)
            bal = ex.fetch_balance()
            krw_free = safe_float(bal.get("KRW", {}).get("free", 0), 0.0)
            btc_total = safe_float(bal.get("BTC", {}).get("total", 0), 0.0)
            avg_buy = parse_avg_buy_price(bal.get("info", None), currency="BTC")
            return label, krw_free, btc_total, avg_buy
        except Exception as e:
            last_err = e
            # A가 IP 막히면 B 시도하는 목적이므로 retryable이면 다음 키로
            if is_retryable_auth_error(e):
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("사용 가능한 키 세트가 없습니다.")

def place_market_buy_upbit(ex, symbol: str, krw_cost: int):
    last_err = None
    try:
        return ex.create_market_buy_order(symbol, krw_cost)
    except Exception as e:
        last_err = e

    try:
        fn = getattr(ex, "create_market_buy_order_with_cost", None)
        if callable(fn):
            return fn(symbol, krw_cost)
    except Exception as e:
        last_err = e

    try:
        return ex.create_order(symbol, "market", "buy", krw_cost, None, {"cost": krw_cost})
    except Exception as e:
        last_err = e

    raise last_err

def place_order_with_fallback(keysets, symbol: str, krw_cost: int):
    last_err = None
    for label, acc, sec in keysets:
        try:
            ex = upbit_private(acc, sec)

            # 잔고 확인
            bal = ex.fetch_balance()
            krw_free = safe_float(bal.get("KRW", {}).get("free", 0), 0.0)
            if krw_free < krw_cost:
                raise RuntimeError(f"KRW 잔고 부족: 보유 {krw_free:,.0f}원 / 필요 {krw_cost:,.0f}원")

            order = place_market_buy_upbit(ex, symbol, krw_cost)
            return label, order

        except Exception as e:
            last_err = e
            if is_retryable_auth_error(e):
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("주문 가능한 키 세트가 없습니다.")

# -------------------------
# (5) 8분할 가중치(1..8)
# -------------------------
def weighted_amount_for_step(budget: int, step: int, n: int = 8):
    step = max(1, min(int(step), int(n)))
    total_w = n * (n + 1) // 2
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

top1, top2, top3 = st.columns([1.2, 1.2, 2.2])
with top1:
    if st.button("🌸 모의투자", use_container_width=True, type=("primary" if S["mode"] == "paper" else "secondary")):
        S["mode"] = "paper"
        clear_errors()
        st.rerun()
with top2:
    if st.button("🚀 실전투자", use_container_width=True, type=("primary" if S["mode"] == "live" else "secondary")):
        S["mode"] = "live"
        clear_errors()
        st.rerun()
with top3:
    st.caption("실전 자동매매는 위험합니다. PIN + 토글 + 확인문구로 잠금 처리했습니다.")

# -------------------------
# 설정 패널(키 2세트 입력 포함)
# -------------------------
def settings_panel(prefix: str):
    st.subheader("⚙️ 설정")

    S["mobile_ui"] = st.toggle("📱 모바일 UI(분봉 selectbox)", value=S.get("mobile_ui", True), key=f"{prefix}_mobile")

    budget = st.number_input(
        "모의 예산(초기/리셋 기준)",
        min_value=1_000_000,
        max_value=500_000_000,
        step=500_000,
        value=int(S["paper"]["budget"]),
        key=f"{prefix}_budget",
    )

    st.markdown("#### 🔑 Upbit Key Set A")
    accA = st.text_input("Access Key A", type="password", key=f"{prefix}_accA")
    secA = st.text_input("Secret Key A", type="password", key=f"{prefix}_secA")

    st.markdown("#### 🔑 Upbit Key Set B")
    accB = st.text_input("Access Key B", type="password", key=f"{prefix}_accB")
    secB = st.text_input("Secret Key B", type="password", key=f"{prefix}_secB")

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
        if st.button("🧹 데이터 초기화(모의/실전봇로그)", use_container_width=True, key=f"{prefix}_reset"):
            b = int(S["paper"]["budget"])
            S["paper"] = {"budget": b, "krw": b, "btc": 0.0, "avg": 0.0, "spent": 0, "logs": []}
            S["live"]["spent"] = 0
            S["live"]["logs"] = []
            S["pin_ok"] = False
            S["pin_fail"] = 0
            S["pin_lock_until"] = 0.0
            clear_errors()
            st.success("초기화 완료")
            st.rerun()

    return accA, secA, accB, secB

with st.expander("🔑 업비트 API 설정(키 2세트) - 연결 후 접어두세요", expanded=False):
    accA_main, secA_main, accB_main, secB_main = settings_panel("main")

with st.sidebar:
    st.header("📌 사이드바(폴드에서 메뉴로 숨겨질 수 있어요)")
    accA_side, secA_side, accB_side, secB_side = settings_panel("side")

# 입력 우선, 비면 secrets 사용
keysets = build_keysets(
    accA_main or accA_side,
    secA_main or secA_side,
    accB_main or accB_side,
    secB_main or secB_side,
)

# =========================================================
# 데이터 계산
# =========================================================
try:
    price = fetch_price()
except Exception as e:
    push_error(e, "시세 조회 실패")
    st.error("📡 시세 연결 실패. [🧯 에러 로그] 탭 확인")
    st.stop()

# 업비트 투자 정보(실전모드일 때만)
used_key_label = None
krw_cash = btc_qty = avg_buy = 0.0
upbit_cost_basis = 0.0

if S["mode"] == "live":
    if keysets:
        try:
            used_key_label, krw_cash, btc_qty, avg_buy = fetch_live_balance_with_fallback(keysets)
            upbit_cost_basis = (btc_qty * avg_buy) if (btc_qty > 0 and avg_buy > 0) else 0.0
        except Exception as e:
            push_error(e, "실전 잔고 조회 실패(A/B 폴백)")
    else:
        st.warning("키 세트가 비어있습니다. Key Set A/B를 입력하거나 Secrets에 등록하세요.")

# 모의모드 데이터
if S["mode"] == "paper":
    p = S["paper"]
    krw_cash = float(p["krw"])
    btc_qty = float(p["btc"])
    avg_buy = float(p["avg"])
    upbit_cost_basis = 0.0  # 모의는 업비트 투자원금 없음

market_value = btc_qty * price
total_asset = krw_cash + market_value
pnl = market_value - upbit_cost_basis
roi = (pnl / upbit_cost_basis * 100.0) if upbit_cost_basis > 0 else 0.0

bot_spent = float(S["paper"]["spent"] if S["mode"] == "paper" else S["live"]["spent"])

# =========================================================
# 메트릭(요청: 업비트 투자정보 + 봇 누적 합산)
# =========================================================
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("🏦 총자산(현금+코인)", f"{total_asset:,.0f}원")
m2.metric("💵 현금(KRW)", f"{krw_cash:,.0f}원")
m3.metric("🎯 평단(Upbit/모의)", (f"{avg_buy:,.0f}원" if avg_buy > 0 else "—"))
m4.metric("🧾 업비트 투자원금(실전)", f"{upbit_cost_basis:,.0f}원" if S["mode"] == "live" else "—")
m5.metric("🤖 봇 누적 매수합", f"{bot_spent:,.0f}원")

d1, d2, d3 = st.columns(3)
d1.metric("💹 코인평가금", f"{market_value:,.0f}원")
d2.metric("🟢 손익(평가-원금)", f"{pnl:,.0f}원" if S["mode"] == "live" else "—")
d3.metric("📈 수익률(Upbit기준)", f"{roi:.2f}%" if S["mode"] == "live" else "—")

if S["mode"] == "live":
    st.caption(f"실전 잔고 조회에 사용된 키: **Key Set {used_key_label if used_key_label else '-'}** (A 실패 시 B로 자동 재시도)")

st.divider()

# =========================================================
# 실전매매 PIN 잠금(요청: 392766 입력창과 일치하면 실전매매 활성화)
#   - PIN은 Secrets(TRADE_PIN)에서 읽고, 없으면 "설정 필요"로 막음(보안)
# =========================================================
EXPECTED_PIN = get_secret("TRADE_PIN")  # 권장: Secrets에 저장
if S["mode"] == "live":
    st.subheader("🔒 실전매매 잠금(PIN)")

    now_ts = time.time()
    if S["pin_lock_until"] > now_ts:
        remain = int(S["pin_lock_until"] - now_ts)
        st.error(f"PIN 입력이 여러 번 틀려 잠금 상태입니다. {remain}s 후 다시 시도하세요.")
    else:
        pin_input = st.text_input("사용자 비번(PIN) 입력", type="password", placeholder="PIN 입력")
        colp1, colp2 = st.columns([1, 1])
        with colp1:
            if st.button("PIN 확인", use_container_width=True):
                if not EXPECTED_PIN:
                    st.error("TRADE_PIN이 설정되어 있지 않습니다. Streamlit Secrets에 TRADE_PIN을 넣어주세요.")
                elif pin_input == EXPECTED_PIN:
                    S["pin_ok"] = True
                    S["pin_fail"] = 0
                    st.success("PIN 확인 완료: 실전 매매 기능이 활성화됩니다.")
                else:
                    S["pin_ok"] = False
                    S["pin_fail"] += 1
                    st.error("PIN이 일치하지 않습니다.")
                    # 5회 실패 시 2분 잠금
                    if S["pin_fail"] >= 5:
                        S["pin_lock_until"] = time.time() + 120
                        st.error("5회 실패로 120초 잠금되었습니다.")
        with colp2:
            if st.button("PIN 잠금 해제(로그아웃)", use_container_width=True):
                S["pin_ok"] = False
                st.warning("실전 매매 잠금 상태로 전환했습니다.")

st.divider()

# =========================================================
# 매수 실행(모의/실전)
# =========================================================
if S["mode"] == "paper":
    done = len(S["paper"]["logs"])
    step = min(done + 1, N_SPLIT)
    budget = int(S["paper"]["budget"])
    amount = weighted_amount_for_step(budget, step, n=N_SPLIT)

    st.caption(f"모의 8분할 가중치 추천: **{step}차 = {amount:,.0f}원** / 예산 {budget:,.0f}원")

    if st.button(
        f"🔥 {step}차 모의 매수 ({amount:,.0f}원)",
        use_container_width=True,
        type="primary",
        disabled=(amount < MIN_ORDER_KRW or step > N_SPLIT),
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
                    "평단(갱신)": float(new_avg),
                    "누적매수합(봇)": int(new_spent),
                })
                clear_errors()
                st.success("모의 매수(기록) 완료")
                st.rerun()
        except Exception as e:
            push_error(e, "모의 매수 실패")
            st.error("모의 매수 오류. [🧯 에러 로그] 확인")

else:
    st.subheader("🚀 실전 시장가 매수(실제 주문)")

    st.info(
        "실전 주문은 실제로 체결됩니다.\n"
        "실전매수 활성화 조건:\n"
        "1) PIN 확인 완료(PIN OK)\n"
        "2) '실전매수 허용' 토글 ON\n"
        "3) 확인문구에 '매수' 입력\n"
        "4) 키 세트(A/B) 중 하나가 인증 성공해야 함\n"
    )

    live_trade_enabled = st.toggle("⚠️ 실전매수 허용", value=False)
    confirm = st.text_input("확인문구(매수)", value="", placeholder="매수")

    done = len(S["live"]["logs"])
    step = min(done + 1, N_SPLIT)
    strategy_budget = int(S["paper"]["budget"])
    rec_amount = weighted_amount_for_step(strategy_budget, step, n=N_SPLIT)

    amount_to_buy = st.number_input(
        "이번 회차 매수금액(KRW) (기본=추천, 필요시 조정)",
        min_value=MIN_ORDER_KRW,
        max_value=100_000_000,
        step=10_000,
        value=int(max(MIN_ORDER_KRW, rec_amount)),
    )

    can_trade = bool(
        S["pin_ok"]
        and live_trade_enabled
        and (confirm.strip() == "매수")
        and keysets
        and amount_to_buy >= MIN_ORDER_KRW
    )

    if st.button(
        f"🚀 {step}차 실전 시장가 매수 실행 ({int(amount_to_buy):,.0f}원)",
        use_container_width=True,
        type="primary",
        disabled=not can_trade,
    ):
        try:
            used_label, order = place_order_with_fallback(keysets, SYMBOL, int(amount_to_buy))

            S["live"]["spent"] = int(S["live"]["spent"] + int(amount_to_buy))
            S["live"]["logs"].append({
                "시간": now_str(),
                "모드": "실전",
                "차수": step,
                "사용키": f"Key Set {used_label}",
                "매수금액(KRW)": int(amount_to_buy),
                "누적매수합(봇)": int(S["live"]["spent"]),
                "결과요약": str(order)[:700],
            })
            clear_errors()
            st.success(f"실전 주문 요청 완료! (사용 키: {used_label}) 업비트에서 체결 확인하세요.")
            st.rerun()

        except Exception as e:
            push_error(e, "실전 매수 실패(A/B 폴백)")
            st.error("실전 매수 오류. [🧯 에러 로그] 탭 확인")

st.divider()

# =========================================================
# Tabs
# =========================================================
tab1, tab2, tab3, tab4 = st.tabs(["📋 기록", "📈 차트", "📊 요약", "🧯 에러 로그"])

with tab1:
    logs = S["paper"]["logs"] if S["mode"] == "paper" else S["live"]["logs"]
    if logs:
        st.dataframe(pd.DataFrame(logs)[::-1], use_container_width=True, hide_index=True)
    else:
        st.write("아직 기록이 없습니다.")

with tab2:
    timeframes = ["1m", "5m", "30m", "1h"]
    tf = st.selectbox("분봉", timeframes, index=2) if S.get("mobile_ui", True) else st.radio("분봉", timeframes, index=2, horizontal=True)

    try:
        df = fetch_ohlcv(tf, limit=80)
        fig = go.Figure(data=[
            go.Candlestick(x=df["dt"], open=df["o"], high=df["h"], low=df["l"], close=df["c"], name="BTC/KRW")
        ])
        if avg_buy and avg_buy > 0:
            fig.add_hline(y=avg_buy, line_dash="dash", line_color="yellow", annotation_text="평단")
        fig.add_hline(y=price, line_dash="dot", line_color="#7ec8ff", annotation_text="현재가")
        fig.update_layout(template="plotly_dark", height=420, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        push_error(e, "차트 로딩 실패")
        st.warning("차트 로딩 실패. [🧯 에러 로그] 확인")

with tab3:
    summary = {
        "UID": UID,
        "모드": "모의" if S["mode"] == "paper" else "실전",
        "Outbound IP": CURRENT_OUTBOUND_IP,
        "현재가": price,
        "KRW 현금": krw_cash,
        "BTC 보유": btc_qty,
        "평단": avg_buy,
        "업비트 투자원금(실전)": upbit_cost_basis,
        "평가금": market_value,
        "손익(실전)": pnl,
        "수익률(실전%)": roi,
        "봇 누적매수합": bot_spent,
        "PIN OK": S["pin_ok"],
    }
    st.dataframe(pd.DataFrame([summary]), use_container_width=True, hide_index=True)
    st.caption("업비트는 로컬에서 보이는 IP와 실제 통신 IP가 다를 수 있다고 안내합니다. [Source](https://docs.upbit.com/kr/docs/faq-api)")

with tab4:
    if not S["errors"]:
        st.success("현재 에러 없음")
    else:
        st.warning(f"에러 {len(S['errors'])}건 (최근 10개)")
        for i, err in enumerate(S["errors"][::-1][:10], start=1):
            title = f"#{i} · {err['time']} · {err['context']} · {err['msg']}"
            with st.expander(title, expanded=False):
                st.code(err["tb"])
