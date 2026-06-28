from __future__ import annotations

import pandas as pd
import yfinance as yf

MANUAL_PRICES = {"QQQI": 54.69, "CASH": 1.0}


def get_price(ticker: str) -> float:
    ticker = ticker.upper().strip()
    if ticker in MANUAL_PRICES:
        return MANUAL_PRICES[ticker]
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            return 0.0
        return float(data["Close"].dropna().iloc[-1])
    except Exception:
        return 0.0


def enrich_prices(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["current_price"] = out["ticker"].apply(get_price)
    out.loc[out["ticker"] == "CASH", "current_price"] = 1.0
    out["market_value"] = out["shares"] * out["current_price"]
    out["cost_basis"] = out["shares"] * out["avg_cost"]
    out["gain_loss"] = out["market_value"] - out["cost_basis"]
    out["gain_loss_pct"] = (out["gain_loss"] / out["cost_basis"].replace(0, pd.NA) * 100).fillna(0)
    total = float(out["market_value"].sum())
    out["weight"] = (out["market_value"] / total * 100).fillna(0) if total else 0
    out["drift"] = out["weight"] - out["target_weight"]
    return out


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        data = yf.Ticker(ticker.upper().strip()).history(period=period)
        if data.empty:
            return pd.DataFrame()
        data = data.reset_index()
        data["Date"] = pd.to_datetime(data["Date"]).dt.date
        return data[["Date", "Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return pd.DataFrame()
