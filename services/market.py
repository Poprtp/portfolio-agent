import pandas as pd
import yfinance as yf


def fetch_price(ticker: str, fallback: float = 0.0) -> tuple[float, str]:
    ticker = str(ticker).upper().strip()
    if ticker == "CASH":
        return 1.0, "cash"
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            return float(fallback or 0), "fallback"
        price = float(data["Close"].dropna().iloc[-1])
        return round(price, 2), "updated"
    except Exception:
        return float(fallback or 0), "fallback"


def price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        data = yf.Ticker(ticker).history(period=period)
        if data.empty:
            return pd.DataFrame()
        return data.reset_index()[["Date", "Close"]]
    except Exception:
        return pd.DataFrame()
