import streamlit as st
import pandas as pd
import math
from datetime import datetime

import pyupbit
import plotly.express as px
import plotly.graph_objects as go


# =========================
# Secrets / Constants
# =========================
# Streamlit Cloud Secrets에 넣은 값 사용:
# APP_PASSWORD = "392766"
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")

MIN_ORDER_KRW = 5000
DEFAULT_CANDLE_COUNT = 200


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="Upbit Dashboard (실전/모의)",
    layout="wide",
    initial_sidebar_state="collapsed",  # 모바일에서 사이드바 겹침 줄이기
)

# =========================
# Style
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

# 실전 4분할 플랜 / 주문 로그
if "real_plans" not in st.session_state:
    st.session_state.real_plans = {}

if "real_trades" not in st.session_state:
    st.session_state.real_trades = []

# Upbit 키: Secrets가 있으면 기본값으로 세팅(모바일 편의)
if "upbit_access_a" not in st.session_state:
    st.session_state.upbit_access_a = st.secrets.get("UPBIT_ACCESS_KEY", "")
if "upbit_secret_a" not in st.session_state:
    st.session_state.upbit_secret_a = st.secrets.get("UPBIT_SECRET_KEY", "")


# =========================
# Price / Candle loaders
# =========================
@st.cache_data(ttl=3, show_spinner=False)
def get_current_prices(tickers):
    if not tickers:
        return {}
    res = pyupbit.get_current_price(list(tickers))
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
# Upbit loaders (Real) - SAFE
# =========================
def load_upbit_balances_safe(access: str, secret: str):
    """
    정상: list[dict]
    실패: dict 형태로 {'error': {'name': ..., 'message': ...}}가 오는 경우가 있음
    -> 그 경우 err를 그대로 반환해서 st.json으로 보여줄 수 있게 함.
    """
    up = pyupbit.Upbit(access, secret)
    res = up.get_balances()

    # 업비트 에러는 dict로 오는 케이스가 있음
    if isinstance(res, dict) and "error" in res:
        return None, res

    if isinstance(res, list):
        return res, None

    # 그 외 예상치 못한 응답
    return None, {"error": {"name": "unexpected_response", "message": str(res)}}


def calc_upbit_kpis(balances: list):
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

        qty_total = _to_float(b.get("balance")) + _to_float(b.get("locked"))
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
# Real trade (4분할) helpers
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

    # 기존 보유정보(표)에서 가져와서 현황표에 같이 표시
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

    remaining = float(plan["total_krw"]) - float(plan["each_krw"]) * float(plan["done"])
    buy_krw = min(float(plan["each_krw"]), max(0.0, remaining))

    if buy_krw < MIN_ORDER_KRW:
        return False, f"남은 예산이 최소주문금액 미만입니다. 남은 예산: {fmt_krw(remaining)}"

    ok, msg = real_buy_market(upbit, ticker, buy_krw)
    if not ok:
        return False, msg

    cur_price = get_price_one(ticker)
    plan["done"] += 1
    if cur_price:
        plan["last_buy_price"] = float(cur_price)
        plan["next_trigger"] = (
            float(cur_price) * (1.0 - float(plan["step_pct"]) / 100.0)
            if plan["done"] < plan["splits"]
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


# =================
