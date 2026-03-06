import streamlit as st
import pandas as pd
import requests
import math
import ccxt
import plotly.express as px


# -------------------------
# Page / CSS
# -------------------------
st.set_page_config(
    page_title="Upbit CCXT Dashboard (실전/모의)",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
h1 { font-size: 1.8rem !important; }
@media (max-width: 768px) {
  h1 { font-size: 1.4rem !important; }
  [data-testid="stSidebar"] { width: 78vw !important; }
  .block-container { padding-left: .8rem; padding-right: .8rem; }
}
</style>
""", unsafe_allow_html=True)


# -------------------------
# Utils
# -------------------------
def fmt_krw(x):
    if x is None:
        return "—"
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return "—"
        return f"{int(round(x)):,}원"
    except:
        return "—"

def fmt_pct(x):
    if x is None:
        return "—"
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return "—"
        return f"{x:.2f}%"
    except:
        return "—"

def safe_div(a, b, default=0.0):
    return default if not b else (a / b)

def get_outbound_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception as e:
        return f"확인 실패: {e}"


# -------------------------
# Password Gate
# -------------------------
def require_password() -> bool:
    if "authorized" not in st.session_state:
        st.session_state.authorized = False

    with st.form("pw_form"):
        pw = st.text_input("실전 비밀번호", type="password")
        ok = st.form_submit_button("확인")

    if ok:
        st.session_state.authorized = (pw == st.secrets.get("APP_PASSWORD", ""))

    return st.session_state.authorized


# -------------------------
# CCXT Upbit init
# -------------------------
def init_upbit_exchange():
    access = st.secrets.get("UPBIT_ACCESS_KEY", "")
    secret = st.secrets.get("UPBIT_SECRET_KEY", "")
    if not access or not secret:
        raise RuntimeError("Secrets에 UPBIT_ACCESS_KEY / UPBIT_SECRET_KEY를 설정해야 합니다.")

    ex = ccxt.upbit({
        "apiKey": access,
        "secret": secret,
        "enableRateLimit": True,
    })
    return ex


# -------------------------
# Upbit raw endpoints via CCXT (Upbit style)
# accounts: GET /v1/accounts
# ticker  : GET /v1/ticker?markets=KRW-BTC,KRW-ETH...
# -------------------------
def fetch_accounts(ex):
    # 반환: list of dict
    return ex.private_get_accounts()

def fetch_ticker_prices_by_market(ex, markets):
    if not markets:
        return {}
    res = ex.public_get_ticker({"markets": ",".join(markets)})
    # res: list[{market, trade_price, ...}]
    return {item["market"]: float(item["trade_price"]) for item in res}


def calc_upbit_kpis_from_accounts(accounts, prices):
    """
    업비트 투자내역 화면과 동일한 구조로 계산:
    - 보유 KRW = KRW balance + KRW locked
    - 총 매수 = Σ(qty_total * avg_buy_price)
    - 총 평가 = Σ(qty_total * 현재가)
    - 평가손익 = 총 평가 - 총 매수
    - 수익률 = 평가손익 / 총 매수
    - 총 보유자산 = 보유 KRW + 총 평가
    """
    krw_cash = 0.0
    rows = []

    total_buy = 0.0
    total_eval = 0.0

    for a in accounts:
        cur = a.get("currency")
        unit = a.get("unit_currency", "KRW")
        bal = float(a.get("balance", 0) or 0)
        locked = float(a.get("locked", 0) or 0)
        qty_total = bal + locked

        if cur == "KRW":
            krw_cash = qty_total
            continue

        market = f"{unit}-{cur}"  # Upbit market format
        avg_buy = float(a.get("avg_buy_price", 0) or 0)

        buy_amt = qty_total * avg_buy
        total_buy += buy_amt

        p = prices.get(market)
        eval_amt = None if p is None else qty_total * float(p)
        if eval_amt is not None:
            total_eval += eval_amt

        profit = None if eval_amt is None else (eval_amt - buy_amt)

        rows.append({
            "마켓": market,
            "수량(보유+묶임)": qty_total,
            "평단": avg_buy,
            "현재가": p,
            "총매수(원금)": buy_amt,
            "총평가": eval_amt,
            "평가손익": profit,
        })

    profit_total = total_eval - total_buy
    profit_rate = (profit_total / total_buy * 100.0) if total_buy > 0 else 0.0
    total_asset = krw_cash + total_eval

    df = pd.DataFrame(rows).sort_values(by="총평가", ascending=False) if rows else pd.DataFrame(rows)

    portfolio = []
    if total_asset > 0:
        portfolio.append({"자산": "KRW", "금액": krw_cash})
        for r in rows:
            if r["총평가"] is not None and r["총평가"] > 0:
                portfolio.append({"자산": r["마켓"], "금액": r["총평가"]})

    return {
        "krw_cash": krw_cash,
        "total_buy": total_buy,
        "total_eval": total_eval,
        "profit": profit_total,
        "profit_rate": profit_rate,
        "total_asset": total_asset,
        "coins_df": df,
        "portfolio_df": pd.DataFrame(portfolio),
    }


# -------------------------
# Mock trading state
# -------------------------
if "mode" not in st.session_state:
    st.session_state.mode = "모의"
if "mock_cash" not in st.session_state:
    st.session_state.mock_cash = 10_000_000.0
if "mock_positions" not in st.session_state:
    st.session_state.mock_positions = {}  # {"KRW-ETH": {"qty":..., "avg":...}}

def mock_buy(market, krw_amount, price):
    if krw_amount <= 0:
        raise ValueError("매수 금액은 0보다 커야 합니다.")
    if st.session_state.mock_cash < krw_amount:
        raise ValueError("모의 KRW가 부족합니다.")
    qty = krw_amount / price

    pos = st.session_state.mock_positions.get(market)
    if not pos:
        st.session_state.mock_positions[market] = {"qty": qty, "avg": price}
    else:
        old_qty = pos["qty"]
        old_avg = pos["avg"]
        new_qty = old_qty + qty
        new_avg = (old_qty * old_avg + qty * price) / new_qty
        st.session_state.mock_positions[market] = {"qty": new_qty, "avg": new_avg}

    st.session_state.mock_cash -= krw_amount

def mock_sell(market, qty, price):
    pos = st.session_state.mock_positions.get(market)
    if not pos:
        raise ValueError("보유 포지션이 없습니다.")
    if qty <= 0 or qty > pos["qty"]:
        raise ValueError("매도 수량이 올바르지 않습니다.")

    st.session_state.mock_cash += qty * price
    pos["qty"] -= qty
    if pos["qty"] <= 1e-12:
        st.session_state.mock_positions.pop(market, None)

def calc_mock_kpis(prices):
    total_buy = 0.0
    total_eval = 0.0
    rows = []
    for m, pos in st.session_state.mock_positions.items():
        qty = float(pos["qty"])
        avg = float(pos["avg"])
        buy_amt = qty * avg
        total_buy += buy_amt
        p = prices.get(m)
        eval_amt = None if p is None else qty * float(p)
        if eval_amt is not None:
            total_eval += eval_amt
        profit = None if eval_amt is None else (eval_amt - buy_amt)

        rows.append({
            "마켓": m,
            "수량": qty,
            "평단": avg,
            "현재가": p,
            "총매수": buy_amt,
            "총평가": eval_amt,
            "평가손익": profit,
        })

    profit_total = total_eval - total_buy
    profit_rate = (profit_total / total_buy * 100.0) if total_buy > 0 else 0.0
    total_asset = st.session_state.mock_cash + total_eval

    df = pd.DataFrame(rows).sort_values(by="총평가", ascending=False) if rows else pd.DataFrame(rows)

    portfolio = [{"자산": "KRW", "금액": st.session_state.mock_cash}]
    for r in rows:
        if r["총평가"] is not None and r["총평가"] > 0:
            portfolio.append({"자산": r["마켓"], "금액": r["총평가"]})

    return {
        "krw_cash": st.session_state.mock_cash,
        "total_buy": total_buy,
        "total_eval": total_eval,
        "profit": profit_total,
        "profit_rate": profit_rate,
        "total_asset": total_asset,
        "coins_df": df,
        "portfolio_df": pd.DataFrame(portfolio),
    }


# =========================
# Sidebar
# =========================
with st.sidebar:
    st.header("설정")
    st.session_state.mode = st.radio("모드 선택", ["모의", "실전"], horizontal=True)

    st.caption(f"서버 Outbound IP(참고): {get_outbound_ip()}")

    if st.session_state.mode == "모의":
        st.subheader("모의 설정")
        st.session_state.mock_cash = float(st.number_input("모의 KRW", min_value=0, step=100_000, value=int(st.session_state.mock_cash)))

        st.subheader("모의 매매")
        mock_market = st.selectbox("마켓", ["KRW-ETH", "KRW-BTC", "KRW-XRP", "KRW-SOL"], index=0)
        mock_buy_krw = st.number_input("매수 금액(원)", min_value=0, step=10_000, value=100_000)
        mock_sell_qty = st.number_input("매도 수량", min_value=0.0, step=0.01, value=0.01, format="%.8f")

        st.caption("모의는 실전키 없이도 작동합니다.")
    else:
        st.subheader("실전 실행")
        st.caption("비번 통과 시에만 실전 API 호출")
        # 실전 비번 폼은 본문에서 보여줄게(UX가 더 좋음)


# =========================
# Main
# =========================
st.title("📊 업비트 CCXT 대시보드 (실전/모의)")

# 공통: 모의용 가격 조회(선택된 것들만)
watch_markets = ["KRW-ETH", "KRW-BTC", "KRW-XRP", "KRW-SOL"]

# --- 모의 ---
if st.session_state.mode == "모의":
    try:
        ex_pub = ccxt.upbit({"enableRateLimit": True})
        prices = fetch_ticker_prices_by_market(ex_pub, watch_markets)

        # 모의 매수/매도 버튼
        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ 모의 매수"):
                p = prices.get(mock_market)
                if p is None:
                    st.error("현재가 조회 실패")
                else:
                    mock_buy(mock_market, float(mock_buy_krw), float(p))
        with colB:
            if st.button("✅ 모의 매도"):
                p = prices.get(mock_market)
                if p is None:
                    st.error("현재가 조회 실패")
                else:
                    mock_sell(mock_market, float(mock_sell_qty), float(p))

        k = calc_mock_kpis(prices)

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
            fig = px.pie(k["portfolio_df"], values="금액", names="자산", hole=0.55, title="포트폴리오(모의)")
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("모의 포지션 상세", expanded=False):
            st.dataframe(k["coins_df"], use_container_width=True)

    except Exception as e:
        st.error("모의 데이터 처리 실패")
        st.code(str(e))

# --- 실전 ---
else:
    if not require_password():
        st.warning("실전 비밀번호를 입력해야 실행됩니다.")
        st.stop()

    try:
        ex = init_upbit_exchange()
        accounts = fetch_accounts(ex)

        # 보유한 코인들 시장 목록 만들기
        markets = []
        for a in accounts:
            if a.get("currency") == "KRW":
                continue
            unit = a.get("unit_currency", "KRW")
            cur = a.get("currency")
            markets.append(f"{unit}-{cur}")

        # 가격 조회
        prices = fetch_ticker_prices_by_market(ex, markets)

        k = calc_upbit_kpis_from_accounts(accounts, prices)

        r1c1, r1c2 = st.columns(2)
        r1c1.metric("보유 KRW", fmt_krw(k["krw_cash"]))
        r1c2.metric("총 보유자산", fmt_krw(k["total_asset"]))

        r2c1, r2c2 = st.columns(2)
        r2c1.metric("총 매수", fmt_krw(k["total_buy"]))
        r2c2.metric("총 평가", fmt_krw(k["total_eval"]))

        r3c1, r3c2 = st.columns(2)
        r3c1.metric("평가손익", fmt_krw(k["profit"]))
        r3c2.metric("수익률", fmt_pct(k["profit_rate"]))

        if not k["portfolio_df"].empty:
            fig = px.pie(k["portfolio_df"], values="금액", names="자산", hole=0.55, title="포트폴리오(실전)")
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("실전 보유자산 상세(평단/현재가/평가손익)", expanded=False):
            st.dataframe(k["coins_df"], use_container_width=True)

    except Exception as e:
        st.error("실전 업비트 로드 실패")
        st.code(str(e))
        st.info("에러에 no_authorization_ip / out_of_scope / jwt_verification 등이 보이면 그 에러코드가 핵심입니다.")
