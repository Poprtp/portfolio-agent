from functools import lru_cache

import yfinance as yf


def _safe_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _label_growth(value):
    if value is None:
        return "Unknown", 0
    if value >= 0.15:
        return "Strong", 18
    if value >= 0.05:
        return "Moderate", 10
    if value >= 0:
        return "Weak", 0
    return "Contracting", -12


def _label_profit(info):
    gross = _safe_float(info.get("grossMargins"))
    operating = _safe_float(info.get("operatingMargins"))
    profit = _safe_float(info.get("profitMargins"))
    fcf = _safe_float(info.get("freeCashflow"))
    earn_growth = _safe_float(info.get("earningsGrowth"))

    positives = 0
    if gross is not None and gross > 0.25:
        positives += 1
    if operating is not None and operating > 0.08:
        positives += 1
    if profit is not None and profit > 0:
        positives += 1
    if fcf is not None and fcf > 0:
        positives += 1
    if earn_growth is not None and earn_growth > 0:
        positives += 1

    if positives >= 4:
        return "Healthy", 18
    if positives >= 2:
        return "Mixed", 8
    if positives == 1:
        return "Weak", -8
    return "Unknown", 0


def _label_valuation(info):
    pe = _safe_float(info.get("forwardPE")) or _safe_float(info.get("trailingPE"))
    ps = _safe_float(info.get("priceToSalesTrailing12Months"))

    if pe is None and ps is None:
        return "Unknown", 0

    high = (pe is not None and pe > 60) or (ps is not None and ps > 20)
    medium = (pe is not None and pe > 30) or (ps is not None and ps > 10)

    if high:
        return "High", -15
    if medium:
        return "Medium", 2
    return "Reasonable", 12


@lru_cache(maxsize=128)
def stock_homework(ticker: str) -> dict:
    """30-minute homework style check from available yfinance fundamentals.

    This is a practical filter, not a full valuation model.
    """
    ticker = str(ticker or "").upper().strip()
    base = {
        "business": "Unknown",
        "growth": "Unknown",
        "profit_quality": "Unknown",
        "valuation": "Unknown",
        "exit_plan": "Stop/Thesis",
        "score": 50,
        "summary": "Fundamental data is limited. Treat this as a technical-only setup until verified.",
        "risks": ["Limited fundamental data"],
    }
    if not ticker:
        return base

    try:
        info = yf.Ticker(ticker).get_info()
    except Exception:
        return base

    if not isinstance(info, dict) or not info:
        return base

    summary = info.get("longBusinessSummary") or ""
    sector = info.get("sector") or info.get("category") or ""
    business_clear = bool(summary or sector or info.get("shortName") or info.get("longName"))
    business = "Clear" if business_clear else "Unclear"

    revenue_growth = _safe_float(info.get("revenueGrowth"))
    growth, growth_score = _label_growth(revenue_growth)
    profit, profit_score = _label_profit(info)
    valuation, valuation_score = _label_valuation(info)

    score = 35
    score += 15 if business == "Clear" else -10
    score += growth_score
    score += profit_score
    score += valuation_score
    score = int(max(0, min(100, score)))

    risks = []
    if growth in ["Weak", "Contracting", "Unknown"]:
        risks.append("Growth driver needs verification")
    if profit in ["Weak", "Unknown"]:
        risks.append("Profit quality is not clearly strong")
    if valuation == "High":
        risks.append("Valuation risk is high")
    if not risks:
        risks.append("Main risk is execution price and market volatility")

    if business == "Clear" and growth in ["Strong", "Moderate"] and profit in ["Healthy", "Mixed"]:
        summary_text = "Business is understandable and fundamentals are acceptable for a watchlist candidate."
    elif valuation == "High":
        summary_text = "Company may be good, but price already carries high expectations."
    else:
        summary_text = "Use technical setup only after verifying business, growth, and earnings quality."

    return {
        "business": business,
        "growth": growth,
        "profit_quality": profit,
        "valuation": valuation,
        "exit_plan": "Technical stop or thesis break",
        "score": score,
        "summary": summary_text,
        "risks": risks[:3],
    }
