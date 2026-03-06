import streamlit as st
import requests
import uuid
import jwt
import hashlib
from urllib.parse import urlencode

APP_TITLE = "💎 업비트 연결 테스트(최소버전)"
UPBIT_API = "https://api.upbit.com"

st.set_page_config(page_title=APP_TITLE, layout="wide")

# =========================
# 1) 최상단: Outbound IP 표시
# =========================
@st.cache_data(ttl=60)
def get_outbound_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=3).text.strip()
    except Exception:
        return requests.get("https://ifconfig.me/ip", timeout=3).text.strip()

def show_ip_top():
    try:
        ip = get_outbound_ip()
        st.info(f"🌐 현재 Outbound IP(업비트 허용 IP에 등록할 값): **{ip}**")
        return ip
    except Exception as e:
        st.warning(f"🌐 Outbound IP 조회 실패: {e}")
        return None

out_ip = show_ip_top()

st.title(APP_TITLE)
st.caption("먼저 잔고/평단/투자원금 불러오기만 안정화합니다. (ccxt 미사용)")

# =========================
# 2) Upbit 인증(JWT) 유틸
# =========================
def make_auth_headers(access_key: str, secret_key: str, query: dict | None = None):
    payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
    }

    # 쿼리가 있는 요청(예: 주문조회/주문) 대비용 - 지금은 잔고조회에선 없어도 됨
    if query:
        query_string = urlencode(query).encode()
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload.update({
            "query_hash": query_hash,
            "query_hash_alg": "SHA512",
        })

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

# =========================
# 3) Public 현재가 (KRW-BTC)
# =========================
@st.cache_data(ttl=2)
def fetch_btc_price_krw():
    # Upbit Quotation API (인증 불필요)
    r = requests.get(f"{UPBIT_API}/v1/ticker", params={"markets": "KRW-BTC"}, timeout=5)
    r.raise_for_status()
    return float(r.json()[0]["trade_price"])

# =========================
# 4) 잔고 조회
# =========================
def fetch_accounts(access_key: str, secret_key: str):
    headers = make_auth_headers(access_key, secret_key)
    r = requests.get(f"{UPBIT_API}/v1/accounts", headers=headers, timeout=7)
    r.raise_for_status()
    return r.json()

def try_fetch_accounts_with_fallback(keysets):
    last_err = None
    for label, ak, sk in keysets:
        if not (ak and sk):
            continue
        try:
            data = fetch_accounts(ak, sk)
            return label, data
        except Exception as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("키가 비어있습니다.")

# =========================
# 5) UI 입력 (Key Set A/B)
# =========================
with st.expander("🔑 업비트 API Key 입력 (A/B 중 1개만 있어도 됨)", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Key Set A")
        access_a = st.text_input("Access Key A", type="password")
        secret_a = st.text_input("Secret Key A", type="password")

    with col2:
        st.subheader("Key Set B")
        access_b = st.text_input("Access Key B", type="password")
        secret_b = st.text_input("Secret Key B", type="password")

    st.caption("업비트는 허용 IP에서만 접속 가능한 구조입니다. 위 Outbound IP를 업비트 허용 IP에 등록하세요. [Source](https://docs.upbit.com/kr/docs/faq-api)")

# =========================
# 6) 실행 버튼
# =========================
if st.button("✅ 업비트 잔고/평단/투자원금 불러오기", use_container_width=True, type="primary"):
    try:
        keysets = [("A", access_a.strip(), secret_a.strip()), ("B", access_b.strip(), secret_b.strip())]
        used_label, accounts = try_fetch_accounts_with_fallback(keysets)

        # 필요한 값 뽑기
        krw_free = 0.0
        btc_qty = 0.0
        btc_avg = 0.0

        for row in accounts:
            cur = row.get("currency")
            bal = float(row.get("balance", 0) or 0)
            avg = float(row.get("avg_buy_price", 0) or 0)

            if cur == "KRW":
                krw_free = bal
            if cur == "BTC":
                btc_qty = bal
                btc_avg = avg

        # 현재가/평가
        price = fetch_btc_price_krw()
        invested = btc_qty * btc_avg if btc_qty > 0 and btc_avg > 0 else 0.0
        valuation = btc_qty * price
        pnl = valuation - invested
        roi = (pnl / invested * 100.0) if invested > 0 else 0.0

        st.success(f"잔고 조회 성공! (사용한 키: {used_label})")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💵 KRW 현금", f"{krw_free:,.0f}원")
        m2.metric("🪙 BTC 수량", f"{btc_qty:.8f}")
        m3.metric("🎯 BTC 평단", f"{btc_avg:,.0f}원" if btc_avg > 0 else "—")
        m4.metric("📌 BTC 현재가", f"{price:,.0f}원")

        a1, a2, a3 = st.columns(3)
        a1.metric("🧾 투자원금(수량×평단)", f"{invested:,.0f}원")
        a2.metric("💹 평가금(수량×현재가)", f"{valuation:,.0f}원")
        a3.metric("🟢 손익", f"{pnl:,.0f}원 ({roi:.2f}%)" if invested > 0 else "—")

        st.divider()
        st.subheader("📋 원본 계정 잔고(Upbit /v1/accounts)")
        st.json(accounts)

    except Exception as e:
        # 업비트는 에러코드로 no_authorization_ip, out_of_scope 등이 나올 수 있음 [Source]
        # https://docs.upbit.com/kr/reference/rest-api-guide
        st.error(f"불러오기 실패: {e}")
        st.info("에러가 'no_authorization_ip'면 허용 IP 문제일 확률이 큽니다. [Source](https://docs.upbit.com/kr/reference/rest-api-guide)")
