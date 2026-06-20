import ccxt
import pandas as pd
import streamlit as st
from ta.momentum import RSIIndicator
import requests

# -----------------------
# CONFIG
# -----------------------
exchange = ccxt.coinbase()

TIMEFRAME_M = "1M"
TIMEFRAME_W = "1w"

MIN_VOLUME = 5_000_000
MIN_MC_PROXY = 50_000_000

# -----------------------
# TELEGRAM (optional)
# -----------------------
TELEGRAM_TOKEN = ""  # add if needed
TELEGRAM_CHAT_ID = ""


def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})


# -----------------------
# DATA FETCH
# -----------------------
def fetch(symbol, tf, limit=100):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        df = pd.DataFrame(data, columns=["t","o","h","l","c","v"])
        return df
    except:
        return None


def compute_rsi(df):
    return RSIIndicator(df["c"], window=14).rsi().iloc[-1]


# -----------------------
# SCORING ENGINE
# -----------------------
def score_coin(monthly_rsi, weekly_rsi, volume, mc_proxy):

    score = 0

    # Oversold strength
    score += (30 - monthly_rsi) * 2

    # Weekly confirmation
    if weekly_rsi > monthly_rsi:
        score += 15
    if weekly_rsi > 40:
        score += 10

    # Volume quality
    score += min(volume / 1_000_000, 50)

    # Market cap proxy (size quality)
    score += min(mc_proxy / 10_000_000, 20)

    return score


# -----------------------
# SCANNER
# -----------------------
def scan():
    markets = exchange.load_markets()

    symbols = [
        s for s in markets
        if s.endswith("/USDT") and markets[s]["active"]
    ]

    results = []

    for sym in symbols:

        m = fetch(sym, TIMEFRAME_M)
        if m is None or len(m) < 20:
            continue

        w = fetch(sym, TIMEFRAME_W)
        if w is None or len(w) < 20:
            continue

        # metrics
        monthly_rsi = compute_rsi(m)
        weekly_rsi = compute_rsi(w)

        volume = m["v"].mean()
        price = m["c"].iloc[-1]

        mc_proxy = price * volume

        # filters
        if volume < MIN_VOLUME:
            continue

        if mc_proxy < MIN_MC_PROXY:
            continue

        if monthly_rsi >= 30:
            continue

        if not (weekly_rsi > monthly_rsi or weekly_rsi > 40):
            continue

        score = score_coin(monthly_rsi, weekly_rsi, volume, mc_proxy)

        results.append({
            "symbol": sym,
            "monthly_rsi": monthly_rsi,
            "weekly_rsi": weekly_rsi,
            "volume": volume,
            "mc_proxy": mc_proxy,
            "score": score
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


# -----------------------
# STREAMLIT UI
# -----------------------
st.set_page_config(page_title="Crypto Alpha Scanner", layout="wide")

st.title("🚀 Binance Alpha Scanner (RSI + Trend + Volume)")

if st.button("Run Scan"):
    with st.spinner("Scanning market..."):
        data = scan()

    if not data:
        st.warning("No setups found.")
    else:
        df = pd.DataFrame(data)

        st.success(f"Found {len(df)} setups")

        st.dataframe(df)

        # top signal alert
        top = df.iloc[0]
        msg = f"🔥 TOP SIGNAL: {top['symbol']} | Score {top['score']:.2f}"
        st.write(msg)

        send_telegram(msg)

        st.bar_chart(df.set_index("symbol")["score"])
