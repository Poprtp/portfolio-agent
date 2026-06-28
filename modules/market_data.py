from __future__ import annotations

import pandas as pd
import yfinance as yf


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def get_latest_prices(tickers: list[str]) -> dict[str, float]:
    prices: dict[str, float] = {}
    clean = [normalize_ticker(t) for t in tickers if normalize_ticker(t) != "CASH"]
    if not clean:
        return prices

    try:
        data = yf.download(clean, period="5d", interval="1d", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"].iloc[-1]
            for ticker in clean:
                value = close.get(ticker)
                prices[ticker] = float(value) if pd.notna(value) else 0.0
        else:
            prices[clean[0]] = float(data["Close"].iloc[-1])
    except Exception:
        for ticker in clean:
            try:
                info = yf.Ticker(ticker).history(period="5d")
                prices[ticker] = float(info["Close"].iloc[-1]) if not info.empty else 0.0
            except Exception:
                prices[ticker] = 0.0

    prices["CASH"] = 1.0
    return prices


def get_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    ticker = normalize_ticker(ticker)
    if ticker == "CASH":
        return pd.DataFrame()
    try:
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        return hist.reset_index()
    except Exception:
        return pd.DataFrame()


def get_basic_info(ticker: str) -> dict:
    ticker = normalize_ticker(ticker)
    if ticker == "CASH":
        return {"symbol": "CASH", "longName": "Cash"}
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}
