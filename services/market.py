import pandas as pd
import yfinance as yf

try:
    import streamlit as st
    cache_data = st.cache_data(ttl=3600, show_spinner=False)
except Exception:  # pragma: no cover
    def cache_data(func=None, **kwargs):
        def decorator(f):
            return f
        return decorator(func) if func else decorator



@cache_data
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



@cache_data
def price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    ticker = str(ticker).upper().strip()
    try:
        data = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        if data.empty:
            return pd.DataFrame()
        return data.reset_index()
    except Exception:
        return pd.DataFrame()



@cache_data
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



@cache_data
def fetch_overnight_quote(ticker: str, fallback: float = 0.0) -> dict:
    """Return an extended-hours quote when yfinance exposes one.

    This is best-effort data. Yahoo/yfinance availability differs by symbol,
    session, and market state. If no pre/post quote is available, the function
    falls back to the latest quote from 1-minute prepost history.
    """
    ticker = str(ticker or "").upper().strip()
    base_fallback = float(fallback or 0)
    result = {
        "ticker": ticker,
        "label": "Unavailable",
        "market_state": "Unknown",
        "regular_price": base_fallback,
        "overnight_price": None,
        "change": None,
        "change_pct": None,
        "source": "fallback",
        "note": "No extended-hours quote available from provider.",
    }
    if not ticker:
        return result

    try:
        symbol = yf.Ticker(ticker)
        info = {}
        try:
            info = symbol.get_info() or {}
        except Exception:
            info = {}

        state = str(info.get("marketState", "Unknown") or "Unknown").upper()
        regular = (
            info.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("previousClose")
            or base_fallback
        )
        previous_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or regular or base_fallback
        pre = info.get("preMarketPrice")
        post = info.get("postMarketPrice")

        label = "Latest quote"
        extended = None
        if state.startswith("PRE") and pre:
            extended = float(pre)
            label = "Pre-market"
        elif state.startswith("POST") and post:
            extended = float(post)
            label = "After-hours"
        elif post:
            extended = float(post)
            label = "After-hours"
        elif pre:
            extended = float(pre)
            label = "Pre-market"

        if extended is None:
            try:
                hist = symbol.history(period="5d", interval="1m", prepost=True)
                if not hist.empty:
                    close = hist["Close"].dropna()
                    if not close.empty:
                        extended = float(close.iloc[-1])
                        label = "Extended / latest"
            except Exception:
                pass

        regular = float(regular or previous_close or base_fallback or 0)
        if regular <= 0 and previous_close:
            regular = float(previous_close or 0)

        result.update(
            {
                "label": label if extended is not None else "Unavailable",
                "market_state": state,
                "regular_price": round(regular, 2) if regular else base_fallback,
                "overnight_price": round(float(extended), 2) if extended is not None else None,
                "source": "yfinance",
            }
        )

        if extended is not None and regular:
            change = float(extended) - regular
            result["change"] = round(change, 2)
            result["change_pct"] = round(change / regular * 100, 2)
            result["note"] = "Extended-hours quote. May be delayed or unavailable for some symbols."
        return result
    except Exception as exc:
        result["note"] = f"Unable to fetch extended-hours quote: {exc}"
        return result
