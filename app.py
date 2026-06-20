import streamlit as st
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
import time

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="Crypto Alpha Scanner",
    layout="wide"
)

EXCHANGES = {
    #"Bybit": ccxt.bybit({"enableRateLimit": True}),
    #"OKX": ccxt.okx({"enableRateLimit": True}),
    "KuCoin": ccxt.kucoin({"enableRateLimit": True}),
    #"Binance": ccxt.binance({"enableRateLimit": True}),
}

DEFAULT_COINS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "LINK/USDT",
    "TAO/USDT",
    "AKT/USDT",
    "ONDO/USDT",
    "AIOZ/USDT",
"WLD/USDT",
"OP/USDT",
"ARB/USDT",
"FET/USDT",
"SUI/USDT",
    "SEI/USDT",
    "AVAX/USDT",
    "RENDER/USDT",
    "SEI/USDT",
    "TIA/USDT",
    "LINK/USDT",
    "APT/USDT",
    "VIRTUAL/USDT",
    "RUNE/USDT",
    "ENA/USDT",
    "LDO/USDT",
]

# =========================
# DATA
# =========================

@st.cache_data(ttl=3600)
def fetch_rsi(exchange_name, symbol):

    exchange = EXCHANGES[exchange_name]

    try:

        weekly = exchange.fetch_ohlcv(
            symbol,
            timeframe="1w",
            limit=100
        )

        monthly = exchange.fetch_ohlcv(
            symbol,
            timeframe="1M",
            limit=100
        )

        wdf = pd.DataFrame(
            weekly,
            columns=["t","o","h","l","c","v"]
        )

        mdf = pd.DataFrame(
            monthly,
            columns=["t","o","h","l","c","v"]
        )

        weekly_rsi = RSIIndicator(
            wdf["c"],
            window=14
        ).rsi().iloc[-1]

        monthly_rsi = RSIIndicator(
            mdf["c"],
            window=14
        ).rsi().iloc[-1]

        price = wdf["c"].iloc[-1]

        volume = wdf["v"].iloc[-1]

        return {
            "symbol": symbol,
            "price": price,
            "weekly_rsi": round(float(weekly_rsi), 2),
            "monthly_rsi": round(float(monthly_rsi), 2),
            "volume": volume
        }

    except:
        return None

# =========================
# SCORING
# =========================

def score(row):

    s = 0

    if row["weekly_rsi"] < 30:
        s += (30 - row["weekly_rsi"]) * 2

    if row["weekly_rsi"] > 60:
        s += 20

    if row["monthly_rsi"] > 60:
        s += 20

    if row["weekly_rsi"] > row["monthly_rsi"]:
        s += 10

    return round(s, 2)

# =========================
# SIDEBAR
# =========================

st.sidebar.title("Scanner Settings")

exchange_name = st.sidebar.selectbox(
    "Exchange",
    list(EXCHANGES.keys())
)

watchlist = st.sidebar.multiselect(
    "Watchlist",
    DEFAULT_COINS,
    default=DEFAULT_COINS
)

oversold_only = st.sidebar.checkbox(
    "Weekly RSI < 30"
)

momentum_only = st.sidebar.checkbox(
    "Weekly RSI > 60 and Monthly RSI > 60"
)

# =========================
# SCAN
# =========================

st.title("🚀 Crypto Alpha Scanner")

rows = []

progress = st.progress(0)

for i, symbol in enumerate(watchlist):

    result = fetch_rsi(
        exchange_name,
        symbol
    )

    if result:

        result["score"] = score(result)

        rows.append(result)

    progress.progress(
        (i + 1) / len(watchlist)
    )

df = pd.DataFrame(rows)

# =========================
# FILTERS
# =========================

if not df.empty:

    if oversold_only:
        df = df[
            df["weekly_rsi"] < 30
        ]

    if momentum_only:
        df = df[
            (df["weekly_rsi"] > 60)
            &
            (df["monthly_rsi"] > 60)
        ]

    df = df.sort_values(
        "score",
        ascending=False
    )

# =========================
# DASHBOARD
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Coins",
        len(df)
    )

with col2:
    if len(df):
        st.metric(
            "Top Score",
            df["score"].max()
        )

with col3:
    if len(df):
        st.metric(
            "Average Weekly RSI",
            round(
                df["weekly_rsi"].mean(),
                2
            )
        )

st.divider()

st.subheader("TradingView Style Scanner")

st.dataframe(
    df,
    use_container_width=True
)

# =========================
# TOP SIGNALS
# =========================

st.subheader("Top Opportunities")

if len(df):

    top5 = df.head(5)

    for _, row in top5.iterrows():

        st.success(
            f"""
            {row['symbol']}

            Score: {row['score']}

            Weekly RSI: {row['weekly_rsi']}

            Monthly RSI: {row['monthly_rsi']}
            """
        )

# =========================
# AUTO REFRESH
# =========================

auto = st.sidebar.checkbox(
    "Auto Refresh"
)

if auto:

    st.sidebar.info(
        "Refreshing every 5 minutes"
    )

    time.sleep(300)

    st.rerun()
