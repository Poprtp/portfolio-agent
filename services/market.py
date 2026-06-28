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


def get_symbol_profile(ticker: str) -> dict:
    ticker = str(ticker).upper().strip()
    if ticker == "CASH":
        return {
            "ticker": "CASH",
            "name": "Cash",
            "sector": "Cash",
            "asset_type": "Cash",
            "target_weight": 10.0,
            "current_price": 1.0,
            "price_status": "cash",
        }

    name = ticker
    sector = ""
    asset_type = "Stock"
    target_weight = 10.0

    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        quote_type = str(info.get("quoteType", "")).upper()
        name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector") or ("ETF / Fund" if quote_type in {"ETF", "MUTUALFUND"} else "")

        if quote_type == "ETF":
            asset_type = "ETF"
            target_weight = 20.0
        elif quote_type == "MUTUALFUND":
            asset_type = "Fund"
            target_weight = 20.0
        elif quote_type == "CRYPTOCURRENCY":
            asset_type = "Crypto"
            target_weight = 5.0
        else:
            asset_type = "Stock"
            target_weight = 10.0
    except Exception:
        pass

    price, status = fetch_price(ticker, 0.0)
    return {
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "asset_type": asset_type,
        "target_weight": target_weight,
        "current_price": price,
        "price_status": status,
    }


def price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        data = yf.Ticker(ticker).history(period=period)
        if data.empty:
            return pd.DataFrame()
        return data.reset_index()[["Date", "Close"]]
    except Exception:
        return pd.DataFrame()
