import pandas as pd

from services.market import price_history


def _atr(data: pd.DataFrame, period: int = 14) -> float:
    if data.empty or len(data) < period + 2:
        return 0.0
    high = data["High"]
    low = data["Low"]
    close = data["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return round(float(tr.rolling(period).mean().iloc[-1]), 2)


def professional_trade_setup(ticker: str) -> dict:
    ticker = str(ticker or "").upper().strip()
    if not ticker:
        return _empty_setup(ticker, "No ticker")

    data = price_history(ticker, "1y")
    if data.empty or len(data) < 80:
        return _empty_setup(ticker, "Insufficient data")

    close = data["Close"].dropna()
    high = data["High"]
    low = data["Low"]
    price = round(float(close.iloc[-1]), 2)
    ma20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
    ma50 = round(float(close.rolling(50).mean().iloc[-1]), 2)
    ma200 = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else ma50
    atr = _atr(data)
    high20 = round(float(high.tail(20).max()), 2)
    low20 = round(float(low.tail(20).min()), 2)
    high60 = round(float(high.tail(60).max()), 2)

    reasons = []
    risks = []
    score = 50

    strong_trend = price > ma20 > ma50 >= ma200
    uptrend = price > ma50 >= ma200
    downtrend = price < ma50 and ma50 < ma200
    extended = atr > 0 and price > ma20 + 1.4 * atr
    near_breakout = high20 > 0 and price >= high20 * 0.97

    if strong_trend:
        score += 20
        trend = "Bullish"
        reasons.append("Bullish trend: price above MA20/MA50/MA200")
    elif uptrend:
        score += 12
        trend = "Constructive"
        reasons.append("Trend is positive above MA50")
    elif downtrend:
        score -= 25
        trend = "Bearish"
        risks.append("Price is below key trend averages")
    else:
        trend = "Neutral"
        risks.append("Trend is mixed")

    if strong_trend and not extended:
        setup_type = "Actionable pullback / continuation"
        entry = price
        stop = max(0.01, min(low20, entry - 1.5 * atr)) if atr else low20
        reasons.append("Not overly extended; entry can be planned near current price")
    elif uptrend and extended:
        setup_type = "Wait for pullback"
        entry = round(max(ma20, price - 1.2 * atr), 2) if atr else ma20
        stop = max(0.01, entry - 1.6 * atr) if atr else low20
        score -= 8
        risks.append("Do not chase extended price; wait closer to MA20")
    elif near_breakout and not downtrend:
        setup_type = "Breakout confirmation"
        entry = round(high20 * 1.01, 2)
        stop = max(0.01, min(ma20, entry - 1.7 * atr)) if atr else ma20
        reasons.append("Breakout level is clear; wait for confirmation")
    else:
        setup_type = "No clean setup"
        entry = round(high20 * 1.01, 2)
        stop = max(0.01, min(low20, entry - 2.0 * atr)) if atr else low20
        score -= 15
        risks.append("No clean professional entry yet")

    entry = round(float(entry), 2)
    stop = round(float(stop), 2)
    if stop >= entry and atr:
        stop = round(max(0.01, entry - 1.5 * atr), 2)
    risk = max(entry - stop, 0)
    target = round(entry + risk * 2.2, 2) if risk else high60
    rr = round((target - entry) / risk, 2) if risk else 0

    if rr >= 2:
        score += 15
        reasons.append("Risk/reward is at least 2R")
    else:
        score -= 15
        risks.append("Risk/reward is not good enough yet")

    if atr and price and atr / price > 0.06:
        score -= 10
        risks.append("Volatility is elevated; reduce size")

    score = int(max(0, min(100, score)))
    if score >= 78:
        decision = "READY"
    elif score >= 58:
        decision = "REVIEW"
    else:
        decision = "WAIT"

    return {
        "ticker": ticker,
        "valid": True,
        "score": score,
        "decision": decision,
        "setup_type": setup_type,
        "trend": trend,
        "current_price": price,
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_reward": rr,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "atr": atr,
        "reasons": reasons[:3],
        "risks": risks[:3],
    }


def _empty_setup(ticker: str, reason: str) -> dict:
    return {
        "ticker": ticker,
        "valid": False,
        "score": 0,
        "decision": "WAIT",
        "setup_type": reason,
        "trend": "Unknown",
        "current_price": 0,
        "entry": 0,
        "stop": 0,
        "target": 0,
        "risk_reward": 0,
        "ma20": 0,
        "ma50": 0,
        "ma200": 0,
        "atr": 0,
        "reasons": [],
        "risks": [reason],
    }
