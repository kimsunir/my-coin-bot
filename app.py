import streamlit as st
import pandas as pd
import math
from datetime import datetime

import pyupbit
import plotly.express as px


# =========================
# Page Config (모바일 레이아웃 개선)
# =========================
st.set_page_config(
    page_title="업비트 대시보드 (실전/모의)",
    layout="wide",
    initial_sidebar_state="collapsed",  # ✅ 모바일에서 기본 접힘
)

# =========================
# CSS (모바일/차트/타이틀 대응)
# =========================
st.markdown(
    """
<style>
/* 제목이 너무 커서 모바일에서 레이아웃 깨지는 걸 방지 */
h1 { font-size: 2.0rem !important; }
h2 { font-size: 1.4rem !important; }

/* 모바일에서 사이드바 폭/본문 패딩 조정 */
@media (max-width: 768px) {
  [data-testid="stSidebar"] { width: 78vw !important; }
  .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
  h1 { font-size: 1.6rem !important; }
}

/* 모의 영역 글씨 더 작게 */
.mock-scope * { font-size: 12px !important; line-height: 1.25 !important; }

/* Plotly 차트가 너무 커서 잘리는 경우 방지 */
.js-plotly-plot, .plot-container { max-height: 360px !important; }
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
# Session init
# =========================
if "mode" not in st.session_state:
    st.session_state.mode = "모의"

if "mock_cash" not in st.session_state:
    st.session_state.mock_cash = 10_000_000.0

# mock_positions 예시:
# {"KRW-ETH": {"qty": 0.5, "avg": 3500000.0}}
if "mock_positions" not in st.session_state:
    st.session_state.mock_positions = {}

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None


# =========================
# Cached price fetch
# =========================
@st.cache_data(ttl=3, show_spinner=False)
def get_current_prices(tickers):
    if not tickers:
        return {}

    # 캐시 해시 안정화를 위해 list -> tuple 권장(선택)
    t = tuple(tickers)

    res = pyupbit.get_current_price(list(t))

    # 1) 단일 티커일 때 float로 오는 케이스 방어
    if isinstance(res, (int, float)):
        return {t[0]: float(res)}

    # 2) 정상 dict 케이스
    if isinstance(res, dict):
        return res

    # 3) None/str/기타 케이스 방어
    return {}


def get_price_one(ticker: str):
    prices = get_current_prices([ticker])
    return prices.get(ticker)


# =========================
# 실전: balances 로드 + 방어
# =========================
def load_upbit_balances_safe(access: str, secret: str):
    """
    정상: list[dict]
    에러: dict(error 구조) or str(문자열 에러/응답)
    """
    up = pyupbit.Upbit(access, secret)
    balances = up.get_balances()

    # ✅ str 방어 (현재 너 에러의 직접 원인) [Source](https://www.genspark.ai/api/files/s/AtxTAEZo)
    if isinstance(balances, str):
        raise RuntimeError(f"업비트 응답이 문자열(str)입니다: {balances}")

    # dict 에러 구조 방어
    if isinstance(balances, dict):
        # 어떤 환경에서는 {"error": {...}} 형태가 올 수 있음
        raise RuntimeError(f"업비트 응답이 dict입니다: {balances}")

    # list 아니면 예외
    if not isinstance(balances, list):
        raise RuntimeError(f"업비트 응답 타입이 예상과 다릅니다: {type(balances)} / {balances}")

    return balances


def calc_upbit_kpis_from_balances(balances: list[dict]):
    # KRW (balance + locked)
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

        coins.append({"ticker": ticker, "qty": qty_total, "avg": avg})
        tickers.append(ticker)

    prices = get_current_prices(tickers)

    total_buy = 0.0   # 총 매수(원금)
    total_eval = 0.0  # 총 평가(평가금)

    rows = []
    for c in coins:
        p = prices.get(c["ticker"])
        buy_amt = c["qty"] * c["avg"]
        total_buy += buy_amt

        eval_amt = None if p is None else c["qty"] * float(p)
        if eval_amt is not None:
            total_eval += eval_amt

        profit = None if eval_amt is None else (eval_amt - buy_amt)

        rows.append({
            "티커": c["ticker"],
            "수량(보유+묶임)": c["qty"],
            "평단": c["avg"],
            "현재가": p,
            "총매수(원금)": buy_amt,
            "총평가": eval_amt,
            "평가손익": profit,
        })

    profit_total = total_eval - total_buy
    profit_rate = (profit_total / total_buy * 100.0) if total_buy > 0 else 0.0
    total_asset = krw_cash + total_eval

    portfolio = []
    if total_asset > 0:
        portfolio.append({"자산": "KRW", "금액": krw_cash})
        for r in rows:
            if r["총평가"] is not None and r["총평가"] > 0:
                portfolio.append({"자산": r["티커"], "금액": r["총평가"]})

    return {
        "krw_cash": krw_cash,
        "total_asset": total_asset,
        "total_buy": total_buy,
        "total_eval": total_eval,
        "profit": profit_total,
        "profit_rate": profit_rate,
        "coins_table": pd.DataFrame(rows),
        "portfolio_df": pd.DataFrame(portfolio),
        "coins_count": len(coins),
        "prices_count": len(prices),
    }


# =========================
# 모의: 매수/매도
# =========================
def mock_buy(ticker: str, krw_amount: float):
    if krw_amount <= 0:
        raise ValueError("매수 금액은 0보다 커야 합니다.")
    if st.session_state.mock_cash < krw_amount:
        raise ValueError("모의 현금이 부족합니다.")

    price = get_price_one(ticker)
    if price is None:
        raise RuntimeError("현재가를 가져오지 못했습니다.")

    qty = krw_amount / float(price)

    pos = st.session_state.mock_positions.get(ticker)
    if pos is None:
        st.session_state.mock_positions[ticker] = {"qty": qty, "avg": float(price)}
    else:
        old_qty = float(pos["qty"])
        old_avg = float(pos["avg"])
        new_qty = old_qty + qty
        new_avg = (old_qty * old_avg + qty * float(price)) / new_qty
        st.session_state.mock_positions[ticker] = {"qty": new_qty, "avg": new_avg}

    st.session_state.mock_cash -= krw_amount


def mock_sell(ticker: str, qty: float):
    pos = st.session_state.mock_positions.get(ticker)
    if not pos:
        raise ValueError("해당 코인을 보유하고 있지 않습니다.")
    if qty <= 0:
        raise ValueError("매도 수량은 0보다 커야 합니다.")

    old_qty = float(pos["qty"])
    if qty > old_qty:
        raise ValueError("보유 수량보다 많이 매도할 수 없습니다.")

    price = get_price_one(ticker)
    if price is None:
        raise RuntimeError("현재가를 가져오지 못했습니다.")

    krw_gain = qty * float(price)
    st.session_state.mock_cash += krw_gain

    new_qty = old_qty - qty
    if new_qty <= 1e-12:
        st.session_state.mock_positions.pop(ticker, None)
    else:
        st.session_state.mock_positions[ticker]["qty"] = new_qty


def calc_mock_kpis():
    tickers = list(st.session_state.mock_positions.keys())
    prices = get_current_prices(tickers)

    total_buy = 0.0
    total_eval = 0.0
    rows = []

    for t, pos in st.session_state.mock_positions.items():
        qty = float(pos["qty"])
        avg = float(pos["avg"])
        buy_amt = qty * avg
        total_buy += buy_amt

        p = prices.get(t)
        eval_amt = None if p is None else qty * float(p)
        if eval_amt is not None:
            total_eval += eval_amt

        profit = None if eval_amt is None else (eval_amt - buy_amt)
        rows.append({
            "티커": t,
            "수량": qty,
            "평단": avg,
            "현재가": p,
            "총매수(원금)": buy_amt,
            "총평가": eval_amt,
            "평가손익": profit,
        })

    profit_total = total_eval - total_buy
    profit_rate = (profit_total / total_buy * 100.0) if total_buy > 0 else 0.0
    total_asset = st.session_state.mock_cash + total_eval

    portfolio = []
    if total_asset > 0:
        portfolio.append({"자산": "KRW", "금액": st.session_state.mock_cash})
        for r in rows:
            if r["총평가"] is not None and r["총평가"] > 0:
                portfolio.append({"자산": r["티커"], "금액": r["총평가"]})

    return {
        "krw_cash": st.session_state.mock_cash,
        "total_asset": total_asset,
        "total_buy": total_buy,
        "total_eval": total_eval,
        "profit": profit_total,
        "profit_rate": profit_rate,
        "coins_table": pd.DataFrame(rows),
        "portfolio_df": pd.DataFrame(portfolio),
    }


# =========================
# Sidebar UI
# =========================
with st.sidebar:
    st.header("설정")

    st.session_state.mode = st.radio(
        "모드 선택",
        ["모의", "실전"],
        index=0 if st.session_state.mode == "모의" else 1,
        horizontal=True,
    )

    st.divider()

    if st.session_state.mode == "모의":
        st.subheader("🧪 모의 투자")

        budget = st.number_input("모의 잔(원)", min_value=0, step=100_000, value=int(st.session_state.mock_cash))
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 현금 적용", use_container_width=True):
                st.session_state.mock_cash = float(budget)
        with c2:
            if st.button("🧹 모의 초기화", use_container_width=True):
                st.session_state.mock_cash = float(budget)
                st.session_state.mock_positions = {}

        st.divider()
        st.subheader("🧾 모의 매매")

        # 자주 쓰는 티커만 기본 제공
        ticker = st.selectbox("티커", ["KRW-ETH", "KRW-BTC", "KRW-XRP", "KRW-SOL"], index=0)
        cur_price = get_price_one(ticker)
        st.caption(f"현재가: {cur_price:,}원" if cur_price else "현재가: —")

        buy_krw = st.number_input("매수 금액(원)", min_value=0, step=10_000, value=100_000)
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("✅ 모의 매수", use_container_width=True):
                try:
                    mock_buy(ticker, float(buy_krw))
                    st.success("모의 매수 완료")
                except Exception as e:
                    st.error(str(e))
        with bc2:
            sell_qty = st.number_input("매도 수량", min_value=0.0, step=0.01, value=0.01, format="%.8f")
            if st.button("✅ 모의 매도", use_container_width=True):
                try:
                    mock_sell(ticker, float(sell_qty))
                    st.success("모의 매도 완료")
                except Exception as e:
                    st.error(str(e))

        st.caption("모의 매매는 mock_cash / mock_positions에 반영되며 손익/수익률이 자동 계산됩니다.")

    else:
        st.subheader("🔐 실전 투자 (Key Set A만)")

        # ✅ B세트 완전 제거
        access = st.text_input("Access Key A", type="password", key="upbit_access_a")
        secret = st.text_input("Secret Key A", type="password", key="upbit_secret_a")

        if st.button("🔄 업비트 새로고침", use_container_width=True):
            st.session_state.last_refresh = datetime.now().isoformat(timespec="seconds")

        st.divider()
        st.subheader("⚠️ 실전 주문(기본 OFF)")
        enable_order = st.checkbox("실전 주문 기능 켜기", value=False)
        st.caption("실수 방지용: 체크해야 주문 버튼이 보입니다.")


# =========================
# Main UI
# =========================
st.title("📊 비트 대시보드 (실전/모의)")

if st.session_state.mode == "모의":
    st.markdown('<div class="mock-scope">', unsafe_allow_html=True)

    k = calc_mock_kpis()

    # 모바일 고려: 2열씩 보여주기
    r1c1, r1c2 = st.columns(2)
    r1c1.metric("보유 KRW(모의)", fmt_krw(k["krw_cash"]))
    r1c2.metric("총 보유자산(모의)", fmt_krw(k["total_asset"]))

    r2c1, r2c2 = st.columns(2)
    r2c1.metric("총 매수(모의)", fmt_krw(k["total_buy"]))
    r2c2.metric("총 평가(모의)", fmt_krw(k["total_eval"]))

    r3c1, r3c2 = st.columns(2)
    r3c1.metric("평가손익(모의)", fmt_krw(k["profit"]))
    r3c2.metric("수익률(모의)", fmt_pct(k["profit_rate"]))

    if not k["portfolio_df"].empty:
        fig = px.pie(k["portfolio_df"], values="금액", names="자산", hole=0.55, title="보유자산 포트폴리오(모의)")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("모의 보유자산 상세", expanded=False):
        st.dataframe(k["coins_table"], use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

else:
    # 실전
    access = st.session_state.get("upbit_access_a", "")
    secret = st.session_state.get("upbit_secret_a", "")
    if not access or not secret:
        st.warning("사이드바에서 실전 Access/Secret Key A를 입력해줘.")
        st.stop()

    try:
        balances = load_upbit_balances_safe(access, secret)
        k = calc_upbit_kpis_from_balances(balances)

        # 업비트 앱 투자내역처럼
        r1c1, r1c2 = st.columns(2)
        r1c1.metric("보유 KRW", fmt_krw(k["krw_cash"]))
        r1c2.metric("총 보유자산", fmt_krw(k["total_asset"]))

        r2c1, r2c2 = st.columns(2)
        r2c1.metric("총 매수", fmt_krw(k["total_buy"]))
        r2c2.metric("총 평가", fmt_krw(k["total_eval"]))

        r3c1, r3c2 = st.columns(2)
        r3c1.metric("평가손익", fmt_krw(k["profit"]))
        r3c2.metric("수익률", fmt_pct(k["profit_rate"]))

        st.caption(
            f"보유코인 {k['coins_count']}개 | 현재가 조회 {k['prices_count']}개"
            + (f" | 마지막 새로고침: {st.session_state.last_refresh}" if st.session_state.last_refresh else "")
        )

        if not k["portfolio_df"].empty:
            fig = px.pie(k["portfolio_df"], values="금액", names="자산", hole=0.55, title="보유자산 포트폴리오(실전)")
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("실전 보유자산 상세(평단/현재가/평가손익)", expanded=False):
            st.dataframe(k["coins_table"], use_container_width=True)

    except Exception as e:
        st.error("업비트 데이터 로드 실패")
        st.code(str(e))
        st.info("지금처럼 str 응답이 오면(= 'str' object...) 키/권한/IP/응답형식을 더 확인해야 합니다.")
