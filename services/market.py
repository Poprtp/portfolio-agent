import pandas as pd
import yfinance as yf


def fetch_price(ticker: str, fallback: float = 0.0) -> float:
    ticker = (ticker or "").upper().strip()
    if ticker == "CASH":
        return 1.0
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            return float(fallback or 0)
        return round(float(data["Close"].dropna().iloc[-1]), 2)
    except Exception:
        return float(fallback or 0)


def price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        data = yf.Ticker(ticker).history(period=period)
        if data.empty:
            return pd.DataFrame()
        return data.reset_index()[["Date", "Close"]]
    except Exception:
        return pd.DataFrame()
