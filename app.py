import streamlit as st
import pandas as pd
import math
from datetime import datetime

import pyupbit
import plotly.express as px
import plotly.graph_objects as go


# =========================
# Constants / Secrets
# =========================
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")  # ✅ Cloud Secrets에서 읽음
MIN_ORDER_KRW = 5000                              # ✅ 업비트 최소 주문금액(일반적으로 5,000원)
DEFAULT_CANDLE_COUNT = 200


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="Upbit Dashboard (실전/모의)",
    layout="wide",
    initial_sidebar_state="collapsed",  # ✅ 모바일에서 사이드바 겹침 방지(필요하면 expanded로 변경)
)

# =========================
# Style (Mock font smaller)
# =========================
st.markdown(
    """
<style>
html, body, [class*="css"] { font-size: 14px; }
.mock-scope * { font-size: 12px !important; line-height: 1.25 !important; }
[data-testid="stMetricLabel"] p { font-size: 12px !important; }
div[data-testid="stHorizontalBlock"] { gap: 0.6rem; }
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Utils
# =========================
def _to_float(x, default=0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def fmt_krw(x):
    if x is None:
        return "—"
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return "—"
        return f"{int(round(x)):,}원"
    except Exception:
        return "—"


def fmt_pct(x):
    if x is None:
        return "—"
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return "—"
        return f"{x:.2f}%"
    except Exception:
        return "—"


def safe_div(a, b, default=0.0):
    return default if not b else (a / b)


def now_str():
    return datetime.now().isoformat(timespec="seconds")


# =========================
# Session State Init
# =========================
if "mode" not in st.session_state:
    st.session_state.mode = "모의"

if "mock_cash" not in st.session_state:
    st.session_state.mock_cash = 10_000_000.0

if "mock_positions" not in st.session_state:
    st.session_state.mock_positions = {}

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None

# ✅ 실전 4분할 플랜 / 주문 로그
if "real_plans" not in st.session_state:
    # { "KRW-ETH": {splits, done, total_krw, each_krw, step_pct, last_buy_price, next_trigger,
    #              existing_qty, existing_avg, existing_buy_est, created_at, updated_at} }
    st.session_state.real_plans = {}

if "real_trades" not in st.session_state:
    st.session_state.real_trades = []


# =========================
# Price / Candle loaders
# =========================
@st.cache_data(ttl=3, show_spinner=False)
def get_current_prices(tickers: list[str]) -> dict:
    if not tickers:
        return {}
    res = pyupbit.get_current_price(list(tickers))
    # ✅ 단일 조회가 float로 오는 경우 방어
    if isinstance(res, (int, float)) and len(tickers) == 1:
        return {tickers[0]: float(res)}
    if isinstance(res, dict):
        return res
    return {}


def get_price_one(ticker: str):
    d = get_current_prices([ticker])
    return d.get(ticker)


@st.cache_data(ttl=10, show_spinner=False)
def load_ohlcv(ticker: str, minute: int, count: int = DEFAULT_CANDLE_COUNT) -> pd.DataFrame:
    interval = f"minute{minute}"
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
    if df is None:
        return pd.DataFrame()
    df = df.copy()
    df.reset_index(inplace=True)
    df.rename(columns={"index": "datetime"}, inplace=True)
    return df


# =========================
# Upbit (Real)
# =========================
def load_upbit_balances(access: str, secret: str):
    up = pyupbit.Upbit(access, secret)
    balances = up.get_balances()
    # 방어: 예상치 못한 형태면 예외 처리
    if not isinstance(balances, list):
        raise ValueError(f"get_balances() returned non-list: {type(balances)} / {balances}")
    return balances


def calc_upbit_kpis(balances: list[dict]):
    """
    업비트 앱 투자내역 KPI에 맞춘 계산:
    - 보유KRW: KRW balance + KRW locked
    - 총매수(원금추정): Σ(qty_total * avg_buy_price) (KRW 제외)
    - 총평가: Σ(qty_total * current_price)
    - 평가손익: 총평가 - 총매수
    - 수익률: 평가손익 / 총매수
    - 총보유자산: 보유KRW + 총평가
    """
    krw_item = next((b for b in balances if b.get("currency") == "KRW"), None)
    krw_cash = 0.0
    if krw_item:
        krw_cash = _to_float(krw_item.get("balance")) + _to_float(krw_item.get("locked"))

    coins = []
    tickers = []
    for b in balances:
        cur = b.get("currency")
        if not cur or cur == "KRW":
            continue

        qty_total = _to_float(b.get("balance")) + _to_float(b.get("locked"))  # ✅ locked 포함
        if qty_total <= 0:
            continue

        unit = b.get("unit_currency") or "KRW"
        ticker = f"{unit}-{cur}"
        avg = _to_float(b.get("avg_buy_price"))

        coins.append({"ticker": ticker, "qty": qty_total, "avg_buy_price": avg})
        tickers.append(ticker)

    prices = get_current_prices(tickers)
    total_buy = 0.0
    total_eval = 0.0
    rows = []

    for c in coins:
        p = prices.get(c["ticker"])
        eval_amt = None
        if p is not None:
            eval_amt = c["qty"] * float(p)
            total_eval += eval_amt

        buy_amt = c["qty"] * c["avg_buy_price"]
        total_buy += buy_amt

        profit = None if eval_amt is None else (eval_amt - buy_amt)

        rows.append(
            {
                "티커": c["ticker"],
                "수량(보유+묶임)": c["qty"],
                "평단": c["avg_buy_price"],
                "현재가": p,
                "총매수(원금추정)": buy_amt,
                "총평가": eval_amt,
                "평가손익": profit,
            }
        )

    profit_total = total_eval - total_buy
    profit_rate = safe_div(profit_total, total_buy, default=0.0) * 100.0 if total_buy > 0 else 0.0
    total_asset = krw_cash + total_eval

    portfolio = []
    if total_asset > 0:
        portfolio.append({"자산": "KRW", "금액": krw_cash, "비중(%)": krw_cash / total_asset * 100})
        for r in rows:
            if r["총평가"] is not None and r["총평가"] > 0:
                portfolio.append({"자산": r["티커"], "금액": r["총평가"], "비중(%)": r["총평가"] / total_asset * 100})

    return {
        "krw_cash": krw_cash,
        "total_buy": total_buy,
        "total_eval": total_eval,
        "profit": profit_total,
        "profit_rate": profit_rate,
        "total_asset": total_asset,
        "coins_table": pd.DataFrame(rows),
        "portfolio_df": pd.DataFrame(portfolio),
        "prices_count": len(prices),
        "coins_count": len(coins),
    }


# =========================
# Real trade helpers
# =========================
def can_place_order(password: str, enable_orders: bool):
    if not enable_orders:
        return False, "주문 활성화 체크가 꺼져 있습니다."
    if not APP_PASSWORD:
        return False, "Secrets에 APP_PASSWORD가 설정되지 않았습니다."
    if password != APP_PASSWORD:
        return False, "비밀번호가 틀렸습니다."
    return True, "OK"


def real_buy_market(upbit: pyupbit.Upbit, ticker: str, krw_amount: float):
    krw_amount = float(krw_amount)
    if krw_amount < MIN_ORDER_KRW:
        return False, f"최소 주문금액 미만입니다. (최소 {fmt_krw(MIN_ORDER_KRW)})"

    try:
        resp = upbit.buy_market_order(ticker, krw_amount)
        st.session_state.real_trades.append(
            {"ts": now_str(), "side": "BUY", "ticker": ticker, "krw": krw_amount, "resp": resp}
        )
        return True, f"주문 요청 완료: {ticker} / {fmt_krw(krw_amount)}"
    except Exception as e:
        st.session_state.real_trades.append(
            {"ts": now_str(), "side": "BUY", "ticker": ticker, "krw": krw_amount, "error": str(e)}
        )
        return False, str(e)


def create_plan_from_current_krw(coins_table: pd.DataFrame, ticker: str, total_krw: float, step_pct: float):
    total_krw = float(total_krw)
    step_pct = float(step_pct)

    if total_krw <= 0:
        return False, "총 예산이 0 이하입니다."
    if step_pct <= 0:
        return False, "하락 트리거(step_pct)는 0보다 커야 합니다."

    each_krw = total_krw / 4.0
    if each_krw < MIN_ORDER_KRW:
        return False, f"회당 매수금이 최소주문금액 미만입니다. (회당 {fmt_krw(each_krw)})"

    # 기존 보유(표)에서 정보 추출(표시용)
    existing_qty = None
    existing_avg = None
    existing_buy_est = None
    if coins_table is not None and not coins_table.empty:
        row = coins_table[coins_table["티커"] == ticker]
        if not row.empty:
            existing_qty = _to_float(row.iloc[0].get("수량(보유+묶임)"))
            existing_avg = _to_float(row.iloc[0].get("평단"))
            existing_buy_est = _to_float(row.iloc[0].get("총매수(원금추정)"))

    st.session_state.real_plans[ticker] = {
        "splits": 4,
        "done": 0,
        "total_krw": total_krw,
        "each_krw": each_krw,
        "step_pct": step_pct,
        "last_buy_price": None,
        "next_trigger": None,
        "existing_qty": existing_qty,
        "existing_avg": existing_avg,
        "existing_buy_est": existing_buy_est,
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    return True, "플랜 생성 완료"


def buy_once_and_update_plan(upbit: pyupbit.Upbit, ticker: str):
    plan = st.session_state.real_plans.get(ticker)
    if not plan:
        return False, "플랜이 없습니다."

    if plan["done"] >= plan["splits"]:
        return False, "이미 4회 모두 완료된 플랜입니다."

    # 이번 회차 매수금액(남은 예산 고려)
    remaining = float(plan["total_krw"]) - float(plan["each_krw"]) * float(plan["done"])
    buy_krw = min(float(plan["each_krw"]), max(0.0, remaining))

    if buy_krw < MIN_ORDER_KRW:
        return False, f"남은 예산이 최소주문금액 미만입니다. 남은 예산: {fmt_krw(remaining)}"

    ok, msg = real_buy_market(upbit, ticker, buy_krw)
    if not ok:
        return False, msg

    cur_price = get_price_one(ticker)
    plan["done"] += 1
    plan["last_buy_price"] = float(cur_price) if cur_price else plan["last_buy_price"]
    plan["next_trigger"] = (
        (float(cur_price) * (1.0 - float(plan["step_pct"]) / 100.0))
        if (cur_price and plan["done"] < plan["splits"])
        else None
    )
    plan["updated_at"] = now_str()
    st.session_state.real_plans[ticker] = plan

    if plan["done"] >= plan["splits"]:
        return True, f"{msg} | ✅ 4분할 완료"
    return True, f"{msg} | 다음 트리거: {float(plan['next_trigger']):,.0f}"


def run_next_split_if_triggered(upbit: pyupbit.Upbit, ticker: str, force: bool = False):
    plan = st.session_state.real_plans.get(ticker)
    if not plan:
        return False, "플랜이 없습니다. 먼저 플랜을 생성하세요."

    if plan["done"] >= plan["splits"]:
        return False, "이미 4회 모두 완료된 플랜입니다."

    cur_price = get_price_one(ticker)
    if cur_price is None or cur_price <= 0:
        return False, "현재가를 불러오지 못했습니다."

    # 1회차는 무조건 가능(플랜 생성 후 바로 1회 시작 버튼을 권장)
    if plan["done"] >= 1 and plan["next_trigger"] is not None:
        triggered = float(cur_price) <= float(plan["next_trigger"])
        if (not triggered) and (not force):
            return False, f"아직 트리거 미도달. 현재가 {float(cur_price):,.0f} / 트리거 {float(plan['next_trigger']):,.0f}"

    return buy_once_and_update_plan(upbit, ticker)


# =========================
# Mock KPI (유지)
# =========================
def calc_mock_kpis(mock_cash: float, mock_positions: dict):
    tickers = list(mock_positions.keys())
    prices = get_current_prices(tickers)

    total_buy = 0.0
    total_eval = 0.0
    rows = []

    for t, pos in mock_positions.items():
        qty = _to_float(pos.get("qty"))
        avg = _to_float(pos.get("avg"))
        buy_amt = qty * avg
        total_buy += buy_amt

        p = prices.get(t)
        eval_amt = None if p is None else qty * float(p)
        if eval_amt is not None:
            total_eval += eval_amt

        profit = None if eval_amt is None else (eval_amt - buy_amt)
        rows.append(
            {"티커": t, "수량": qty, "평단": avg, "현재가": p, "총매수(원금)": buy_amt, "총평가": eval_amt, "평가손익": profit}
        )

    profit_total = total_eval - total_buy
    profit_rate = safe_div(profit_total, total_buy, default=0.0) * 100.0 if total_buy > 0 else 0.0
    total_asset = mock_cash + total_eval

    portfolio = []
    if total_asset > 0:
        portfolio.append({"자산": "KRW", "금액": mock_cash, "비중(%)": mock_cash / total_asset * 100})
        for r in rows:
            if r["총평가"] is not None and r["총평가"] > 0:
                portfolio.append({"자산": r["티커"], "금액": r["총평가"], "비중(%)": r["총평가"] / total_asset * 100})

    return {
        "krw_cash": mock_cash,
        "total_buy": total_buy,
        "total_eval": total_eval,
        "profit": profit_total,
        "profit_rate": profit_rate,
        "total_asset": total_asset,
        "coins_table": pd.DataFrame(rows),
        "portfolio_df": pd.DataFrame(portfolio),
    }


# =========================
# Sidebar
# =========================
with st.sidebar:
    st.title("설정")

    st.session_state.mode = st.radio(
        "모드 선택",
        ["모의", "실전"],
        index=0 if st.session_state.mode == "모의" else 1,
        horizontal=True,
    )

    st.divider()

    if st.session_state.mode == "실전":
        st.subheader("🔐 Upbit Key Set A (실전)")

        # ✅ Secrets에 키가 있으면 기본값으로 채움(모바일 편의)
        default_access = st.secrets.get("UPBIT_ACCESS_KEY", "")
        default_secret = st.secrets.get("UPBIT_SECRET_KEY", "")

        st.text_input("Access Key A", type="password", key="upbit_access_a", value=default_access)
        st.text_input("Secret Key A", type="password", key="upbit_secret_a", value=default_secret)

        st.caption("요구사항 반영: 실전에서는 B세트를 완전히 제거했습니다.")

        st.divider()
        st.subheader("🧨 주문 안전장치")
        # ✅ key 지정(중요)
        st.checkbox("주문(실전 매수) 활성화", value=False, key="enable_orders")
        st.text_input("비밀번호(주문 실행)", type="password", key="order_pw")

        do_refresh = st.button("🔄 업비트 새로고침", use_container_width=True)
        if do_refresh:
            st.session_state.last_refresh = now_str()

        st.caption("Secrets 적용은 약 1분 후 반영될 수 있습니다.")

    else:
        st.subheader("🧪 모의 투자")
        budget = st.number_input(
            "모의 예산(원)",
            min_value=0,
            step=100_000,
            value=int(st.session_state.mock_cash),
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 예산 적용", use_container_width=True):
                st.session_state.mock_cash = float(budget)
        with c2:
            if st.button("🧹 모의 초기화", use_container_width=True):
                st.session_state.mock_cash = float(budget)
                st.session_state.mock_positions = {}

        st.caption("모의는 KPI/포트폴리오 확인용으로 유지(실전은 버튼 눌렀을 때만 매수).")


# =========================
# Main UI
# =========================
st.title("📊 업비트 대시보드 (실전/모의)")


def render_candle_chart(ticker: str, minute: int, avg_buy_price: float | None):
    df = load_ohlcv(ticker, minute, DEFAULT_CANDLE_COUNT)
    if df.empty:
        st.warning("분봉 데이터를 불러오지 못했습니다.")
        return

    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["datetime"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=f"{ticker} 캔들",
        )
    )
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["ma20"], mode="lines", name="MA20"))
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["ma60"], mode="lines", name="MA60"))

    if avg_buy_price and avg_buy_price > 0:
        fig.add_hline(
            y=float(avg_buy_price),
            line_width=2,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"평단 {float(avg_buy_price):,.0f}",
            annotation_position="top left",
        )

    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=40, b=10),
        title=f"{ticker} 동향 (분봉: {minute}분, 캔들 {DEFAULT_CANDLE_COUNT}개)",
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True)


if st.session_state.mode == "실전":
    st.subheader("실전 투자 (Key Set A만 사용)")

    access = st.session_state.get("upbit_access_a", "").strip()
    secret = st.session_state.get("upbit_secret_a", "").strip()

    enable_orders = st.session_state.get("enable_orders", False)
    order_password = st.session_state.get("order_pw", "")

    if not access or not secret:
        st.warning("사이드바에서 실전 Access/Secret Key A를 입력하거나 Secrets에 UPBIT_ACCESS_KEY/UPBIT_SECRET_KEY를 넣어줘.")
        st.stop()

    try:
        balances = load_upbit_balances(access, secret)
        k = calc_upbit_kpis(balances)

        # KPI
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("보유 KRW", fmt_krw(k["krw_cash"]))
        a2.metric("총 보유자산", fmt_krw(k["total_asset"]))
        a3.metric("총 매수", fmt_krw(k["total_buy"]))
        a4.metric("총 평가", fmt_krw(k["total_eval"]))

        b1, b2 = st.columns(2)
        b1.metric("평가손익", fmt_krw(k["profit"]))
        b2.metric("수익률", fmt_pct(k["profit_rate"]))

        st.caption(
            f"데이터: 보유코인 {k['coins_count']}개, 현재가 조회 {k['prices_count']}개"
            + (f" | 마지막 새로고침: {st.session_state.last_refresh}" if st.session_state.last_refresh else "")
        )

        # 포트폴리오
        if not k["portfolio_df"].empty:
            figp = px.pie(
                k["portfolio_df"],
                values="금액",
                names="자산",
                title="보유자산 포트폴리오(실전)",
                hole=0.55,
            )
            st.plotly_chart(figp, use_container_width=True)

        # ✅ 1) 기존 투자현황 표
        st.markdown("### ✅ 실전 현재 투자현황(업비트에서 불러온 보유/평단/평가손익)")
        st.dataframe(k["coins_table"], use_container_width=True)

        # 티커 후보
        tickers_from_holdings = []
        if k["coins_table"] is not None and not k["coins_table"].empty:
            tickers_from_holdings = sorted(k["coins_table"]["티커"].dropna().unique().tolist())

        st.divider()

        # ✅ 2) 매수현황 표(기존투자 표 아래에 고정 표시)
        st.markdown("### 📋 매수현황(실전 4분할)")
        # 티커 선택(현황 표/차트도 이 티커 기준)
        if tickers_from_holdings:
            real_ticker = st.selectbox("대상 티커", tickers_from_holdings, index=0, key="real_ticker_sel")
        else:
            real_ticker = st.text_input("대상 티커(예: KRW-ETH)", value="KRW-ETH", key="real_ticker_txt")

        plan = st.session_state.real_plans.get(real_ticker)
        cur_price = get_price_one(real_ticker)

        if plan:
            status_df = pd.DataFrame([{
                "티커": real_ticker,
                "진행": f"{plan['done']}/{plan['splits']}",
                "총 예산": plan["total_krw"],
                "회당 매수": plan["each_krw"],
                "하락 트리거(%)": plan["step_pct"],
                "마지막 매수가": plan["last_buy_price"],
                "다음 트리거": plan["next_trigger"],
                "현재가": cur_price,
                "기존 보유수량": plan.get("existing_qty"),
                "기존 평단": plan.get("existing_avg"),
                "기존 원금추정": plan.get("existing_buy_est"),
                "생성": plan["created_at"],
                "업데이트": plan["updated_at"],
            }])
            st.dataframe(status_df, use_container_width=True)
        else:
            st.info("아직 4분할 플랜이 없어. 아래에서 '시작(플랜+1회 매수)'를 누르면 1회부터 들어갑니다.")

        st.divider()

        # ✅ 3) 실전 4분할 매수 컨트롤
        st.markdown("### 🛒 실전 4분할 매수")

        # 현재 선택 코인의 평단(차트에 표시)
        avg_buy_price = None
        if k["coins_table"] is not None and not k["coins_table"].empty:
            row = k["coins_table"][k["coins_table"]["티커"] == real_ticker]
            if not row.empty:
                avg_buy_price = _to_float(row.iloc[0].get("평단"))

        c1, c2 = st.columns([2, 1])
        with c1:
            total_krw = st.number_input(
                "이번 4분할 총 예산(원) (플랜 기준)",
                min_value=0,
                step=100_000,
                value=1_000_000,
                key="real_total_krw_4",
            )
        with c2:
            step_pct = st.number_input(
                "하락 트리거(%)",
                min_value=0.1,
                step=0.1,
                value=2.0,
                key="real_step_pct_4",
            )

        up = pyupbit.Upbit(access, secret)

        b1, b2, b3 = st.columns(3)

        with b1:
            if st.button("🚀 시작(플랜 생성 + 1회 매수)", use_container_width=True):
                ok, msg = can_place_order(order_password, enable_orders)
                if not ok:
                    st.warning(msg)
                else:
                    ok2, msg2 = create_plan_from_current_krw(k["coins_table"], real_ticker, float(total_krw), float(step_pct))
                    if not ok2:
                        st.error(msg2)
                    else:
                        ok3, msg3 = buy_once_and_update_plan(up, real_ticker)
                        (st.success if ok3 else st.error)(msg3)

        with b2:
            if st.button("▶ 다음 1회 실행(조건 충족 시)", use_container_width=True):
                ok, msg = can_place_order(order_password, enable_orders)
                if not ok:
                    st.warning(msg)
                else:
                    ok2, msg2 = run_next_split_if_triggered(up, real_ticker, force=False)
                    (st.success if ok2 else st.info)(msg2)

        with b3:
            if st.button("⚠ 강제 1회 매수(조건 무시)", use_container_width=True):
                ok, msg = can_place_order(order_password, enable_orders)
                if not ok:
                    st.warning(msg)
                else:
                    ok2, msg2 = run_next_split_if_triggered(up, real_ticker, force=True)
                    (st.success if ok2 else st.warning)(msg2)

        st.divider()

        # ✅ 4) 코인 동향 차트(분봉 + 평단)
        st.markdown("### 📈 코인 동향 차트 (분봉 + 평균매수가 표시)")
        minute = st.selectbox("분봉", [1, 3, 5, 15, 30, 60, 240], index=3, key="minute_sel")
        render_candle_chart(real_ticker, int(minute), avg_buy_price)

        # ✅ 5) 주문 로그
        if st.session_state.real_trades:
            with st.expander("🧾 실전 주문 로그(최근 200개)", expanded=False):
                st.dataframe(pd.DataFrame(st.session_state.real_trades).tail(200), use_container_width=True)

    except Exception as e:
        st.error("업비트 데이터 로드 실패")
        st.code(str(e))
        st.info("주문/조회가 실패하면 업비트는 error code(예: no_authorization_ip 등)를 응답합니다. 에러 문자열을 그대로 공유해주면 원인 판별이 빠릅니다. [Source](https://docs.upbit.com/kr/reference/rest-api-guide)")
        st.stop()

else:
    st.subheader("모의 투자")
    st.markdown('<div class="mock-scope">', unsafe_allow_html=True)

    k = calc_mock_kpis(st.session_state.mock_cash, st.session_state.mock_positions)

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("보유 KRW(모의)", fmt_krw(k["krw_cash"]))
    a2.metric("총 보유자산(모의)", fmt_krw(k["total_asset"]))
    a3.metric("총 매수(모의)", fmt_krw(k["total_buy"]))
    a4.metric("총 평가(모의)", fmt_krw(k["total_eval"]))

    b1, b2 = st.columns(2)
    b1.metric("평가손익(모의)", fmt_krw(k["profit"]))
    b2.metric("수익률(모의)", fmt_pct(k["profit_rate"]))

    if not k["portfolio_df"].empty:
        fig = px.pie(
            k["portfolio_df"],
            values="금액",
            names="자산",
            title="보유자산 포트폴리오(모의)",
            hole=0.55,
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("모의 보유자산 상세", expanded=False):
        st.dataframe(k["coins_table"], use_container_width=True)
        st.caption("모의는 유지. 핵심은 실전은 버튼 눌렀을 때만 주문이 나가게 구성됨.")

    st.markdown("</div>", unsafe_allow_html=True)
