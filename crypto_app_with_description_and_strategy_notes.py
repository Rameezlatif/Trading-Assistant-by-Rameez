
import streamlit as st
import pandas as pd
import ccxt
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator
import plotly.graph_objects as go

# ------------------------
# Configuration
# ------------------------
st.set_page_config(page_title="Crypto Trading Assistant", layout="wide")
st.title("📈 Crypto Spot Trading Assistant")

st.markdown("""
## Welcome to the Crypto Spot Trading Assistant 🚀

This tool analyzes **live Binance crypto/USDT pairs** using:

- EMA 20 & 50
- RSI (14)
- MACD
- Stochastic Oscillator
- Bollinger Bands
- Support & Resistance
- Volume Confirmation (OBV)
- SL/TP Estimation

### 📌 Strategy Note

This is a **basic but sound momentum strategy** suitable for **manual confirmation**, not automatic trading (yet).

To make it more robust:
- ✅ Add **backtesting**
- ✅ Include **SL/TP calculator**
- ✅ Confirm signals with **volume trends**

---
""")

@st.cache_data(ttl=3600)
def get_usdt_pairs():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    return sorted([s for s in markets if s.endswith("/USDT") and ":" not in s])

# Sidebar
symbol = st.sidebar.selectbox("Select Pair", get_usdt_pairs())
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"])
limit = st.sidebar.slider("Number of candles", 100, 1000, 300)

def load_ohlcv(symbol, timeframe, limit):
    exchange = ccxt.binance()
    data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

df = load_ohlcv(symbol, timeframe, limit)

# Indicators
df["EMA20"] = EMAIndicator(df["close"], window=20).ema_indicator()
df["EMA50"] = EMAIndicator(df["close"], window=50).ema_indicator()
df["RSI"] = RSIIndicator(df["close"], window=14).rsi()

macd = MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
df["MACD"] = macd.macd()
df["MACD_signal"] = macd.macd_signal()

stoch = StochasticOscillator(df["high"], df["low"], df["close"], window=14, smooth_window=3)
df["Stoch_K"] = stoch.stoch()
df["Stoch_D"] = stoch.stoch_signal()

bb = BollingerBands(df["close"], window=20, window_dev=2)
df["BB_upper"] = bb.bollinger_hband()
df["BB_lower"] = bb.bollinger_lband()
df["BB_middle"] = bb.bollinger_mavg()

df["support"] = df["low"].rolling(window=20).min()
df["resistance"] = df["high"].rolling(window=20).max()

# Volume Indicator
df["OBV"] = OnBalanceVolumeIndicator(df["close"], df["volume"]).on_balance_volume()

# SL/TP Placeholder
latest_close = df["close"].iloc[-1]
sl = latest_close * 0.98
tp = latest_close * 1.02

# Plotting
fig = go.Figure()
fig.add_trace(go.Candlestick(x=df["timestamp"],
                             open=df["open"], high=df["high"],
                             low=df["low"], close=df["close"], name="Candles"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["EMA20"], line=dict(color="blue"), name="EMA20"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["EMA50"], line=dict(color="red"), name="EMA50"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["BB_upper"], line=dict(color="gray", dash="dot"), name="BB Upper"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["BB_lower"], line=dict(color="gray", dash="dot"), name="BB Lower"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["support"], line=dict(color="green", dash="dash"), name="Support"))
fig.add_trace(go.Scatter(x=df["timestamp"], y=df["resistance"], line=dict(color="orange", dash="dash"), name="Resistance"))

fig.update_layout(title=f"{symbol} Price Chart with Indicators", xaxis_title="Time", yaxis_title="Price")
st.plotly_chart(fig, use_container_width=True)

# Signals
latest = df.iloc[-1]
signal = "⚪ Neutral"
if latest["EMA20"] > latest["EMA50"] and latest["RSI"] < 70 and latest["MACD"] > latest["MACD_signal"]:
    signal = "🟢 Buy"
elif latest["EMA20"] < latest["EMA50"] and latest["RSI"] > 70 and latest["MACD"] < latest["MACD_signal"]:
    signal = "🔴 Sell"

st.subheader("Signal Summary")
st.write(f"**Current Signal:** {signal}")
st.metric("RSI", f"{latest['RSI']:.2f}")
st.metric("MACD", f"{latest['MACD']:.2f}", delta=f"{latest['MACD'] - latest['MACD_signal']:.2f}")
st.metric("OBV", f"{latest['OBV']:.2f}")
st.metric("Price", f"{latest_close:.2f} USDT")
st.metric("Estimated SL", f"{sl:.2f} USDT")
st.metric("Estimated TP", f"{tp:.2f} USDT")
