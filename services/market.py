import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

FALLBACK_PRICES = {
    "QQQI": 54.69,
    "TSM": 432.35,
    "NVDA": 192.53,
    "AVGO": 365.02,
    "MSFT": 372.97,
    "CASH": 1.0,
}


@st.cache_data(ttl=900)
def get_current_price(ticker: str) -> float:
    ticker = ticker.upper().strip()
    if ticker == "CASH":
        return 1.0
    if yf is None:
        return FALLBACK_PRICES.get(ticker, 0.0)
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            return FALLBACK_PRICES.get(ticker, 0.0)
        return float(data["Close"].dropna().iloc[-1])
    except Exception:
        return FALLBACK_PRICES.get(ticker, 0.0)


@st.cache_data(ttl=1800)
def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    ticker = ticker.upper().strip()
    if yf is None or ticker == "CASH":
        return pd.DataFrame()
    try:
        data = yf.Ticker(ticker).history(period=period).reset_index()
        return data[["Date", "Close"]] if not data.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
