from __future__ import annotations

import pandas as pd
import yfinance as yf

FALLBACK_PRICES = {
    "QQQI": 54.69,
    "TSM": 432.35,
    "NVDA": 192.53,
    "AVGO": 365.02,
    "MSFT": 372.97,
    "GOOGL": 190.00,
    "AMZN": 220.00,
    "META": 700.00,
    "CASH": 1.0,
}


def get_price(ticker: str) -> float:
    ticker = ticker.upper().strip()
    if ticker == "CASH":
        return 1.0
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if not hist.empty:
            return float(hist["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return float(FALLBACK_PRICES.get(ticker, 0.0))


def enrich_prices(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["current_price"] = out["ticker"].apply(get_price)
    out["market_value"] = out["shares"] * out["current_price"]
    invested = out["shares"] * out["avg_cost"]
    out["gain_loss"] = out["market_value"] - invested
    out["gain_loss_pct"] = (out["gain_loss"] / invested.replace(0, pd.NA) * 100).fillna(0)
    total = out["market_value"].sum()
    out["weight"] = (out["market_value"] / total * 100).fillna(0) if total else 0
    out["drift"] = out["weight"] - out["target_weight"]
    return out


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    if ticker.upper() == "CASH":
        return pd.DataFrame()
    try:
        data = yf.Ticker(ticker).history(period=period)
        if data.empty:
            return pd.DataFrame()
        data = data.reset_index()
        data["Date"] = pd.to_datetime(data["Date"]).dt.date
        return data
    except Exception:
        return pd.DataFrame()
