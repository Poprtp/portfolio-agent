import pandas as pd
import yfinance as yf


def fetch_price(ticker: str, fallback: float = 0.0):
    ticker = str(ticker).upper().strip()
    if ticker == "CASH":
        return 1.0, "updated"
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d")
        if hist.empty:
            return float(fallback or 0), "fallback"
        price = round(float(hist["Close"].dropna().iloc[-1]), 2)
        return price, "updated"
    except Exception:
        return float(fallback or 0), "fallback"


def price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    ticker = str(ticker).upper().strip()
    try:
        data = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        if data.empty:
            return pd.DataFrame()
        return data.reset_index()
    except Exception:
        return pd.DataFrame()


def get_symbol_profile(ticker: str) -> dict:
    ticker = str(ticker).upper().strip()
    price, _ = fetch_price(ticker, 0)
    profile = {
        "ticker": ticker,
        "name": ticker,
        "asset_type": "Stock",
        "sector": "",
        "target_weight": 10.0,
        "current_price": price,
    }
    try:
        info = yf.Ticker(ticker).get_info()
        quote_type = str(info.get("quoteType", "EQUITY")).upper()
        profile["name"] = info.get("shortName") or info.get("longName") or ticker
        if quote_type in ["ETF", "MUTUALFUND"]:
            profile["asset_type"] = "ETF"
            profile["sector"] = info.get("category") or "ETF"
            profile["target_weight"] = 15.0
        else:
            profile["asset_type"] = "Stock"
            profile["sector"] = info.get("sector") or "Stock"
            profile["target_weight"] = 10.0
    except Exception:
        pass
    return profile
