from __future__ import annotations

import pandas as pd
import yfinance as yf


def get_latest_price(ticker: str, fallback: float = 0.0) -> float:
    if not ticker or ticker.upper() == "CASH":
        return float(fallback or 1.0)
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d")
        if hist.empty:
            return float(fallback or 0.0)
        price = float(hist["Close"].dropna().iloc[-1])
        return round(price, 4)
    except Exception:
        return float(fallback or 0.0)


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    if not ticker or ticker.upper() == "CASH":
        return pd.DataFrame()
    try:
        hist = yf.Ticker(ticker).history(period=period, interval="1d").reset_index()
        if hist.empty:
            return pd.DataFrame()
        return hist[["Date", "Close"]]
    except Exception:
        return pd.DataFrame()
