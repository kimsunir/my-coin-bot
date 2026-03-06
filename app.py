import streamlit as st
import pandas as pd
import math
from datetime import datetime

import pyupbit
import plotly.express as px


# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="Upbit Dashboard (실전/모의)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# Style (Mock font smaller)
# =========================
st.markdown(
    """
<style>
/* 전체 기본 폰트 약간 다운(모바일 대비) */
html, body, [class*="css"] { font-size: 14px; }

/* 모의 영역만 더 작게 */
.mock-scope * {
  font-size: 12px !important;
  line-height: 1.25 !important;
}

/* metric 라벨 폰트 */
[data-testid="stMetricLabel"] p { font-size: 12px !important; }

/* 카드 간격 조금 줄이기 */
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


# =========================
# Session State Init
# =========================
if "mode" not in st.session_state:
    st.session_state.mode = "모의"

if "mock_cash" not in st.session_state:
    st.session_state.mock_cash = 10_000_000.0  # 기본 모의 예산

# 모의 포지션 예시 구조: { "KRW-ETH": {"qty": 0.12, "avg": 3500000.0}, ... }
if "mock_positions" not in st.session_state:
    st.session_state.mock_positions = {}

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None


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
        upbit_access = st.text_input("Access Key A", type="password", key="upbit_access_a")
        upbit_secret = st.text_input("Secret Key A", type="password", key="upbit_secret_a")

        st.caption("요구사항 반영: 실전에서는 B세트를 완전히 제거했습니다.")

        do_refresh = st.button("🔄 업비트 새로고침", use_container_width=True)
        if do_refresh:
            st.session_state.last_refresh = datetime.now().isoformat(timespec="seconds")

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

        st.caption("모의 포지션(mock_positions)이 연결되면 수익률/손익이 자동 계산됩니다.")


# =========================
# Upbit loaders (Real)
# =========================
@st.cache_data(ttl=3, show_spinner=False)
def get_current_prices(tickers: list[str]) -> dict:
    if not tickers:
        return {}
    return pyupbit.get_current_price(tickers) or {}


def load_upbit_balances(access: str, secret: str):
    up = pyupbit.Upbit(access, secret)
    return up.get_balances()


def calc_upbit_kpis(balances: list[dict]):
    """
    업비트 앱 '투자내역'과 맞추기 위한 KPI:
    - 보유KRW: KRW balance + KRW locked
    - 총매수: Σ(qty_total * avg_buy_price)  (KRW 제외)
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

        coins.append(
            {
                "ticker": ticker,
                "currency": cur,
                "qty": qty_total,
                "avg_buy_price": avg,
            }
        )
        tickers.append(ticker)

    prices = get_current_prices(tickers)
    total_buy = 0.0
    total_eval = 0.0

    rows = []
    for c in coins:
        p = prices.get(c["ticker"])
        if p is None:
            # 가격 못가져오면 평가 계산에서 제외 (표에는 표시)
            eval_amt = None
        else:
            eval_amt = c["qty"] * float(p)
            total_eval += eval_amt

        buy_amt = c["qty"] * c["avg_buy_price"]
        total_buy += buy_amt

        profit = None if (eval_amt is None) else (eval_amt - buy_amt)
        rows.append(
            {
                "티커": c["ticker"],
                "수량(보유+묶임)": c["qty"],
                "평단": c["avg_buy_price"],
                "현재가": p,
                "총매수(원금)": buy_amt,
                "총평가": eval_amt,
                "평가손익": profit,
            }
        )

    profit_total = total_eval - total_buy
    profit_rate = safe_div(profit_total, total_buy, default=0.0) * 100.0 if total_buy > 0 else 0.0
    total_asset = krw_cash + total_eval

    # 포트폴리오 비중(업비트 화면처럼 KRW vs 코인)
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
# Mock loaders
# =========================
def calc_mock_kpis(mock_cash: float, mock_positions: dict):
    """
    mock_positions 예시:
      {
        "KRW-ETH": {"qty": 0.12, "avg": 3500000.0},
        "KRW-BTC": {"qty": 0.001, "avg": 98000000.0},
      }
    """
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
            {
                "티커": t,
                "수량": qty,
                "평단": avg,
                "현재가": p,
                "총매수(원금)": buy_amt,
                "총평가": eval_amt,
                "평가손익": profit,
            }
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
# Main UI
# =========================
st.title("📊 업비트 대시보드 (실전/모의)")

if st.session_state.mode == "실전":
    st.subheader("실전 투자 (Key Set A만 사용)")

    access = st.session_state.get("upbit_access_a", "")
    secret = st.session_state.get("upbit_secret_a", "")

    if not access or not secret:
        st.warning("사이드바에서 실전 Access/Secret Key A를 입력해줘.")
        st.stop()

    try:
        balances = load_upbit_balances(access, secret)
        k = calc_upbit_kpis(balances)

        # --- KPI (업비트 앱 투자내역과 동일 라벨로 출력) ---
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

        # --- Portfolio chart ---
        if not k["portfolio_df"].empty:
            fig = px.pie(
                k["portfolio_df"],
                values="금액",
                names="자산",
                title="보유자산 포트폴리오(실전)",
                hole=0.55,
            )
            st.plotly_chart(fig, use_container_width=True)

        # --- Detail table ---
        with st.expander("실전 보유자산 상세(평단/현재가/평가손익)", expanded=False):
            st.dataframe(k["coins_table"], use_container_width=True)

    except Exception as e:
        st.error("업비트 데이터 로드 실패")
        st.code(str(e))

        st.info(
            "만약 에러에 `no_authorization_ip`가 보이면, 업비트 허용 IP(고정 IP/서버 IP) 문제일 가능성이 큽니다."
        )
        st.stop()

else:
    st.subheader("모의 투자")
    st.markdown('<div class="mock-scope">', unsafe_allow_html=True)

    # 모의 KPI
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
        st.caption("모의 포지션은 st.session_state.mock_positions에 연결하면 자동 계산됩니다.")

    st.markdown("</div>", unsafe_allow_html=True)
