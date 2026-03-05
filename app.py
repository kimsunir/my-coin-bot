import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime
from math import floor

# =========================
# v40 - 부석 거미줄 시스템
# =========================

st.set_page_config(page_title="부석 거미줄 v40", layout="wide")

APP_NAME = "💎 부석 거미줄 v40"
SYMBOL = "BTC/KRW"

# ---- 모바일에서 분봉 라디오가 숨는 문제를 줄이기 위한 힌트 ----
# 완벽한 모바일 감지는 어렵지만, 폴드/모바일 위주로 기본을 selectbox로 두고
# PC에서만 라디오로 쓰고 싶으면 아래 값을 False로 바꿔도 됩니다.
DEFAULT_MOBILE_UI = True

# -------------------------
# Session State 초기화/마이그레이션
# -------------------------
def init_state():
    # paper(모의) 계정 구조
    if "paper" not in st.session_state:
        st.session_state.paper = {
            "budget": 10_000_000,   # 초기 예산
            "krw": 10_000_000,      # 현금
            "btc": 0.0,             # BTC 수량
            "avg": 0.0,             # 평단
            "spent": 0,             # 총매수원금(원금)
            "logs": [],             # 매수 기록
        }

    # 실전모드: 주문은 안하지만 신호 기록은 남길 수 있게
    if "live_logs" not in st.session_state:
        st.session_state.live_logs = []

    # 모드
    if "mode" not in st.session_state:
        # "paper" 또는 "live"
        st.session_state.mode = "paper"

    # UI
    if "mobile_ui" not in st.session_state:
        st.session_state.mobile_ui = DEFAULT_MOBILE_UI

    # 예전(v39) 구조가 있으면 일부 마이그레이션(있을 때만)
    # st.session_state.m = {"y":..., "inv":..., "avg":..., "logs":[]}
    if "m" in st.session_state and "paper" in st.session_state:
        m = st.session_state.m
        p = st.session_state.paper
        # 가능한 범위에서만 이전값 반영
        if isinstance(m, dict) and "y" in m and "avg" in m and "inv" in m:
            p["krw"] = float(m.get("y", p["krw"]))
            p["avg"] = float(m.get("avg", p["avg"]))
            p["spent"] = int(m.get("inv", p["spent"]))
            # btc 수량은 평단이 있으면 환산
            if p["avg"] > 0:
                p["btc"] = p["spent"] / p["avg"]
            # logs는 그대로
            if "logs" in m and isinstance(m["logs"], list) and not p["logs"]:
                p["logs"] = m["logs"]

init_state()


# -------------------------
# Upbit (공용/실전) 유틸
# -------------------------
@st.cache_data(ttl=3)
def fetch_price():
    up = ccxt.upbit({"enableRateLimit": True})
    return float(up.fetch_ticker(SYMBOL)["last"])

@st.cache_data(ttl=10)
def fetch_ohlcv(timeframe: str, limit: int = 80):
    up = ccxt.upbit({"enableRateLimit": True})
    ohlcv = up.fetch_ohlcv(SYMBOL, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["t", "o", "h", "l", "c", "v"])
    df["dt"] = pd.to_datetime(df["t"], unit="ms")
    return df

def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def parse_upbit_avg_buy_price(info_obj, currency="BTC"):
    """
    ccxt.upbit fetch_balance()의 info 구조가 환경/버전별로 다를 수 있어
    최대한 방어적으로 avg_buy_price를 찾습니다.
    못 찾으면 0.0 리턴.
    """
    try:
        # 흔한 케이스: info가 리스트이고 각 원소에 currency/avg_buy_price가 있음
        if isinstance(info_obj, list):
            for row in info_obj:
                if isinstance(row, dict) and row.get("currency") == currency:
                    return safe_float(row.get("avg_buy_price", 0), 0.0)

        # 혹시 dict 안에 리스트가 중첩된 케이스 탐색
        if isinstance(info_obj, dict):
            # upbit에서 'data' 또는 'balances' 같은 키에 들어있기도 함
            for key in ["data", "balances", "result", "info"]:
                if key in info_obj:
                    v = info_obj[key]
                    avg = parse_upbit_avg_buy_price(v, currency=currency)
                    if avg > 0:
                        return avg
    except:
        pass
    return 0.0

def fetch_live_balance(access_key: str, secret_key: str):
    """
    실전: 주문은 하지 않지만 잔고/평단/원금을 표시하기 위해 조회.
    실패 시 예외를 그대로 올려서 화면에서 원인 보이게 함.
    """
    ex = ccxt.upbit({
        "apiKey": access_key,
        "secret": secret_key,
        "enableRateLimit": True,
    })
    bal = ex.fetch_balance()

    krw_free = safe_float(bal.get("KRW", {}).get("free", 0), 0.0)
    btc_total = safe_float(bal.get("BTC", {}).get("total", 0), 0.0)

    info = bal.get("info", None)
    avg_buy = parse_upbit_avg_buy_price(info, currency="BTC")

    return {
        "krw_free": krw_free,
        "btc_total": btc_total,
        "avg_buy": avg_buy,
        "raw": bal,
    }


# -------------------------
# 8분할 가중치 매수금액(1..8)
# -------------------------
def weighted_amount_for_step(budget: int, step: int, n: int = 8):
    """
    budget 내에서 1..n 가중치로 배분.
    amount(step) = floor(budget * step / sum(1..n))
    단, 마지막(step==n)은 반올림 오차를 흡수하기 위해 '남은 금액'으로 맞춥니다.
    """
    step = int(step)
    n = int(n)
    if step < 1:
        step = 1
    if step > n:
        step = n

    total_w = n * (n + 1) // 2  # 36 (n=8)
    if step < n:
        return int(floor(budget * (step / total_w)))
    # 마지막은 남은 금액 = budget - sum(1..n-1)
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

def now_kst_like():
    # 서버 타임존이 다를 수 있어도 일단 스트링 기록용
    return datetime.now().strftime("%m/%d %H:%M:%S")


# -------------------------
# 설정 패널(사이드바 + 본문 expander 둘 다 쓸 함수)
# -------------------------
def settings_panel(prefix: str):
    st.subheader("⚙️ 설정")
    colA, colB = st.columns([1, 1])

    with colA:
        st.session_state.mobile_ui = st.toggle(
            "📱 모바일 UI(분봉 selectbox)",
            value=st.session_state.mobile_ui,
            key=f"{prefix}_mobile_ui",
        )
    with colB:
        budget = st.number_input(
            "모의 예산(초기)",
            min_value=1_000_000,
            max_value=500_000_000,
            step=500_000,
            value=int(st.session_state.paper["budget"]),
            key=f"{prefix}_budget",
        )

    st.caption("실전모드는 **주문 실행 없이** 잔고/평단만 조회합니다. (업비트 앱에서 직접 매매)")

    # 키 입력(실전 조회용)
    access_key = st.text_input("Upbit Access Key", type="password", key=f"{prefix}_acc")
    secret_key = st.text_input("Upbit Secret Key", type="password", key=f"{prefix}_sec")

    # 예산 변경 적용(버튼 방식으로 적용)
    apply_budget = st.button("💾 모의 예산 적용", use_container_width=True, key=f"{prefix}_apply_budget")
    if apply_budget:
        # 예산을 바꾸면 현금도 같이 리셋해주는 게 보통 기대 동작
        st.session_state.paper = {
            "budget": int(budget),
            "krw": int(budget),
            "btc": 0.0,
            "avg": 0.0,
            "spent": 0,
            "logs": [],
        }
        st.success("모의 예산을 적용하고 모의 계정을 초기화했습니다.")
        st.rerun()

    # 컨트롤 버튼
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 화면 새로고침", use_container_width=True, key=f"{prefix}_rerun"):
            st.rerun()
    with c2:
        if st.button("🧹 데이터 초기화", use_container_width=True, key=f"{prefix}_reset"):
            st.session_state.paper = {
                "budget": int(st.session_state.paper["budget"]),
                "krw": int(st.session_state.paper["budget"]),
                "btc": 0.0,
                "avg": 0.0,
                "spent": 0,
                "logs": [],
            }
            st.session_state.live_logs = []
            st.success("초기화 완료")
            st.rerun()

    return access_key, secret_key


# -------------------------
# 상단 헤더 + 모드 버튼(모의/실전)
# -------------------------
st.title(APP_NAME)

top1, top2, top3 = st.columns([1.2, 1.2, 1])
with top1:
    if st.button("🌸 모의투자 모드", use_container_width=True, type=("primary" if st.session_state.mode=="paper" else "secondary")):
        st.session_state.mode = "paper"
        st.rerun()
with top2:
    if st.button("🚀 실전투자 모드(조회전용)", use_container_width=True, type=("primary" if st.session_state.mode=="live" else "secondary")):
        st.session_state.mode = "live"
        st.rerun()
with top3:
    if st.button("🔄 새로고침", use_container_width=True):
        st.rerun()

# v31 화면처럼 "업비트 API 설정(접어서)" 느낌을 그대로 제공 [Source]
with st.expander("🔑 업비트 API 설정 (연결 후 접어두세요)", expanded=False):
    access_key_main, secret_key_main = settings_panel(prefix="main")

# 사이드바도 같이 제공(폴드에서 메뉴 숨김 대비)
with st.sidebar:
    st.header("📌 사이드바(모바일에서 안 보이면 위 설정 펼치기 사용)")
    access_key_side, secret_key_side = settings_panel(prefix="side")

# 키 입력은 둘 중 하나라도 채워진 것을 사용
ACCESS_KEY = access_key_main or access_key_side
SECRET_KEY = secret_key_main or secret_key_side


# -------------------------
# 핵심 데이터 계산(모의/실전)
# -------------------------
price = None
price_err = None
try:
    price = fetch_price()
except Exception as e:
    price_err = e

if price_err:
    st.error(f"📡 시세 연결 실패: {price_err}")
    st.stop()

# 모드별 계정 상태
if st.session_state.mode == "paper":
    p = st.session_state.paper

    krw_cash = float(p["krw"])
    btc_qty = float(p["btc"])
    avg_buy = float(p["avg"])
    cost_basis = float(p["spent"])  # 원금(총매수)
    market_value = btc_qty * price
    total_asset = krw_cash + market_value
    pnl = market_value - cost_basis
    roi = (pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0
    mode_label = "🌸 모의"

else:
    # 실전 조회
    if not (ACCESS_KEY and SECRET_KEY):
        st.warning("실전모드: Upbit 키를 입력해야 잔고/평단을 가져올 수 있어요. (주문은 실행하지 않습니다)")
        live = {"krw_free": 0.0, "btc_total": 0.0, "avg_buy": 0.0}
    else:
        try:
            live = fetch_live_balance(ACCESS_KEY, SECRET_KEY)
        except Exception as e:
            st.error(f"업비트 잔고 조회 실패: {e}")
            live = {"krw_free": 0.0, "btc_total": 0.0, "avg_buy": 0.0}

    krw_cash = float(live.get("krw_free", 0.0))
    btc_qty = float(live.get("btc_total", 0.0))
    avg_buy = float(live.get("avg_buy", 0.0))
    cost_basis = (btc_qty * avg_buy) if (btc_qty > 0 and avg_buy > 0) else 0.0
    market_value = btc_qty * price
    total_asset = krw_cash + market_value
    pnl = market_value - cost_basis
    roi = (pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0
    mode_label = "🚀 실전(조회전용)"


# -------------------------
# 메트릭(총자산/현금/수익률/평단)
# -------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("🏦 총 자산(현금+코인)", fmt_krw(total_asset))
m2.metric("💵 현금", fmt_krw(krw_cash))
m3.metric("📈 수익률", fmt_pct(roi))
m4.metric("🎯 평단", fmt_krw(avg_buy) if avg_buy > 0 else "—")

# 추가 디버깅/가시성(원금/평가/손익)
d1, d2, d3 = st.columns(3)
d1.metric("🧾 매수원금(원금)", fmt_krw(cost_basis))
d2.metric("💹 코인평가금", fmt_krw(market_value))
d3.metric("🟢 손익", fmt_krw(pnl))

st.divider()


# -------------------------
# 매수(신호) 버튼: 8분할 가중치(1..8)
# -------------------------
N_SPLIT = 8
if st.session_state.mode == "paper":
    done_steps = len(st.session_state.paper["logs"])
    step = min(done_steps + 1, N_SPLIT)
    budget = int(st.session_state.paper["budget"])
    amount = weighted_amount_for_step(budget, step, n=N_SPLIT)

    st.caption(f"8분할 가중치(1..8) 기반 추천 매수금액: **{step}차 = {amount:,.0f}원** / 예산 {budget:,.0f}원")

    buy_btn = st.button(
        f"🔥 {step}차 매수 실행 ({amount:,.0f}원)  — 모의",
        use_container_width=True,
        type="primary",
        disabled=(step > N_SPLIT or amount <= 0),
    )

    if buy_btn:
        p = st.session_state.paper
        if p["krw"] < amount:
            st.warning("모의 현금이 부족합니다. 예산/현금 확인!")
        else:
            # 모의 체결: amount 만큼 BTC를 매수했다고 가정(수수료는 단순화)
            btc_bought = amount / price
            new_btc = p["btc"] + btc_bought
            new_spent = p["spent"] + int(amount)

            # 새 평단 = 총원금 / 총수량
            new_avg = (new_spent / new_btc) if new_btc > 0 else 0.0

            p["krw"] -= int(amount)
            p["btc"] = new_btc
            p["spent"] = new_spent
            p["avg"] = new_avg

            p["logs"].append({
                "시간": now_kst_like(),
                "차수": step,
                "매수금액(KRW)": int(amount),
                "체결가": float(price),
                "매수수량(BTC)": float(btc_bought),
                "평단(갱신)": float(new_avg),
            })
            st.success("모의 매수(기록) 완료!")
            st.rerun()

else:
    # 실전모드에서는 주문 금지: 신호만 기록
    done_steps = len(st.session_state.live_logs)
    step = min(done_steps + 1, N_SPLIT)

    # 실전에서는 '예산'이 계좌현금과 다를 수 있어 기준을 2가지 제공:
    # 1) 모의 예산 기반(전략 기준)
    # 2) 현재 KRW 현금 기반(현실 기준)
    strategy_budget = int(st.session_state.paper["budget"])
    amount_strategy = weighted_amount_for_step(strategy_budget, step, n=N_SPLIT)
    amount_by_cash = min(amount_strategy, int(krw_cash)) if krw_cash > 0 else amount_strategy

    st.info(
        "실전모드는 **주문을 실행하지 않습니다.**\n\n"
        f"- 추천 {step}차 매수금액(전략 예산 기준): **{amount_strategy:,.0f}원**\n"
        f"- 현재 KRW 현금 고려 추천: **{amount_by_cash:,.0f}원**\n\n"
        "→ 업비트 앱에서 직접 주문하세요."
    )

    sig_btn = st.button(
        f"📝 {step}차 매수 신호 기록 ({amount_by_cash:,.0f}원) — 실전(조회전용)",
        use_container_width=True,
        type="primary",
        disabled=(step > N_SPLIT or amount_by_cash <= 0),
    )
    if sig_btn:
        st.session_state.live_logs.append({
            "시간": now_kst_like(),
            "차수": step,
            "추천매수금액(KRW)": int(amount_by_cash),
            "현재가": float(price),
            "메모": "업비트 앱에서 수동 매수",
        })
        st.success("신호 기록 완료(주문 없음)")
        st.rerun()


# -------------------------
# 탭: (v31 느낌 유지) 매수정보 / 수익변화 / 비트코인차트 [Source]
# -------------------------
tab1, tab2, tab3 = st.tabs(["📋 매수 정보표", "📊 수익 변화율", "📈 비트코인 차트"])

with tab1:
    if st.session_state.mode == "paper":
        logs = st.session_state.paper["logs"]
        if logs:
            st.table(pd.DataFrame(logs)[::-1])
        else:
            st.write("아직 매수 기록이 없어요.")
    else:
        logs = st.session_state.live_logs
        if logs:
            st.table(pd.DataFrame(logs)[::-1])
        else:
            st.write("아직 신호 기록이 없어요(실전모드는 주문 없음).")

with tab2:
    # 수익 변화율: 간단히 현재 기준 지표 + (모의는 로그 기준으로) 시각화
    st.subheader("📊 수익/원금/평가 요약")
    summary = pd.DataFrame([{
        "모드": mode_label,
        "현재가": price,
        "BTC수량": btc_qty,
        "평단": avg_buy,
        "원금": cost_basis,
        "평가": market_value,
        "손익": pnl,
        "수익률(%)": roi,
    }])
    st.dataframe(summary, use_container_width=True, hide_index=True)

    if st.session_state.mode == "paper" and st.session_state.paper["logs"]:
        st.subheader("📉 모의: 차수별 평단 변화")
        df = pd.DataFrame(st.session_state.paper["logs"])
        df["차수"] = df["차수"].astype(int)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["차수"],
            y=df["평단(갱신)"],
            mode="lines+markers",
            name="평단(갱신)",
        ))
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("모의모드에서 매수 기록이 쌓이면 평단 변화 그래프가 표시됩니다.")

with tab3:
    st.subheader("📈 비트코인 차트")

    # 분봉 선택: 모바일에서 가로 라디오가 안 보이는 문제를 피하기 위해 기본은 selectbox
    timeframes = ["1m", "5m", "30m", "1h"]
    if st.session_state.mobile_ui:
        tf = st.selectbox("분봉", timeframes, index=2)
    else:
        tf = st.radio("분봉", timeframes, index=2, horizontal=True)

    df = fetch_ohlcv(tf, limit=80)

    fig = go.Figure(data=[
        go.Candlestick(
            x=df["dt"],
            open=df["o"], high=df["h"], low=df["l"], close=df["c"],
            name="BTC/KRW"
        )
    ])

    # 평단선(노란 점선)
    if avg_buy and avg_buy > 0:
        fig.add_hline(y=avg_buy, line_dash="dash", line_color="yellow", annotation_text="평단", annotation_position="top left")

    # 현재가 라인(연한 하늘색)
    fig.add_hline(y=price, line_dash="dot", line_color="#7ec8ff", annotation_text="현재가", annotation_position="bottom left")

    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

    if st.session_state.mode == "live":
        st.caption("실전 매매는 업비트 앱에서 확인/진행하세요. (본 앱은 조회/신호용)")


# v31 화면에도 안내문이 있었던 것처럼 하단 안내 [Source]
st.divider()
if st.session_state.mode == "live":
    st.info("✅ 실전 매매는 업비트 앱에서 하세요! (이 앱은 잔고/평단 조회 + 신호 기록용)")
else:
    st.caption("모의모드: 매수 버튼은 실제 주문이 아닌 '기록/시뮬레이션'입니다.")
