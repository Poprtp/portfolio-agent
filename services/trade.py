from datetime import datetime

import pandas as pd
import yfinance as yf

from services.database import connect


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


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
    """Generate a rule-based long trade setup from price action.

    This is not a prediction and does not place orders. It creates a structured setup
    similar to how a discretionary trader would frame entry, stop, and target.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return {
            "ticker": "",
            "valid": False,
            "recommendation": "WAIT",
            "confidence": 0,
            "entry": 0.0,
            "stop": 0.0,
            "target": 0.0,
            "current_price": 0.0,
            "setup_type": "No ticker",
            "trend": "Unknown",
            "momentum": "Unknown",
            "reason": "Enter a ticker first.",
            "reasons": [],
            "risks": ["No ticker entered"],
        }

    try:
        data = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
    except Exception as exc:
        return {
            "ticker": ticker,
            "valid": False,
            "recommendation": "WAIT",
            "confidence": 0,
            "entry": 0.0,
            "stop": 0.0,
            "target": 0.0,
            "current_price": 0.0,
            "setup_type": "Data unavailable",
            "trend": "Unknown",
            "momentum": "Unknown",
            "reason": f"Could not load market data: {exc}",
            "reasons": [],
            "risks": ["Market data unavailable"],
        }

    data = data.dropna(subset=["Close"])
    if data.empty or len(data) < 60:
        return {
            "ticker": ticker,
            "valid": False,
            "recommendation": "WAIT",
            "confidence": 0,
            "entry": 0.0,
            "stop": 0.0,
            "target": 0.0,
            "current_price": 0.0,
            "setup_type": "Insufficient data",
            "trend": "Unknown",
            "momentum": "Unknown",
            "reason": "Not enough price history to create a reliable setup.",
            "reasons": [],
            "risks": ["Insufficient price history"],
        }

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    price = round(float(close.iloc[-1]), 2)
    ma20 = round(float(close.rolling(20).mean().iloc[-1]), 2)
    ma50 = round(float(close.rolling(50).mean().iloc[-1]), 2)
    ma200 = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(data) >= 200 else ma50
    atr = _atr(data)
    high20 = round(float(high.tail(20).max()), 2)
    low20 = round(float(low.tail(20).min()), 2)
    high60 = round(float(high.tail(60).max()), 2)
    low60 = round(float(low.tail(60).min()), 2)

    reasons = []
    risks = []
    score = 50

    uptrend = price > ma50 and ma50 >= ma200
    strong_uptrend = price > ma20 > ma50 >= ma200
    downtrend = price < ma50 and ma50 < ma200

    if strong_uptrend:
        trend = "Bullish"
        momentum = "Strong"
        score += 25
        reasons.append("Price is above MA20/MA50/MA200 with bullish alignment")
    elif uptrend:
        trend = "Bullish"
        momentum = "Moderate"
        score += 15
        reasons.append("Price remains above MA50 and long-term trend is positive")
    elif downtrend:
        trend = "Bearish"
        momentum = "Weak"
        score -= 20
        risks.append("Price is below MA50 and trend is weak")
    else:
        trend = "Neutral"
        momentum = "Mixed"
        risks.append("Trend is mixed, setup needs confirmation")

    extended = atr > 0 and price > ma20 + 1.5 * atr
    near_breakout = price >= high20 * 0.98

    if strong_uptrend and not extended:
        setup_type = "Trend continuation"
        entry = price
        stop = max(0.01, min(low20, entry - 1.5 * atr)) if atr else low20
        reasons.append("Current price is not overly extended from MA20")
    elif uptrend and extended:
        setup_type = "Pullback buy"
        entry = max(ma20, price - 1.2 * atr) if atr else ma20
        stop = max(0.01, entry - 1.5 * atr) if atr else low20
        risks.append("Price is extended; better entry is on pullback")
    elif near_breakout and not downtrend:
        setup_type = "Breakout confirmation"
        entry = round(high20 * 1.01, 2)
        stop = max(0.01, min(ma20, entry - 1.7 * atr)) if atr else ma20
        reasons.append("Price is close to a 20-day breakout zone")
    else:
        setup_type = "Wait for confirmation"
        entry = round(high20 * 1.01, 2)
        stop = max(0.01, min(low20, entry - 2.0 * atr)) if atr else low20
        risks.append("Professional setup prefers confirmation before entry")

    entry = round(float(entry), 2)
    stop = round(float(stop), 2)
    if stop >= entry and atr:
        stop = round(max(0.01, entry - 1.5 * atr), 2)
    risk_per_share = max(entry - stop, 0)
    target = round(entry + risk_per_share * 2.3, 2) if risk_per_share else round(high60, 2)

    # If target is unrealistically below recent resistance, keep 2.3R. If recent high is close,
    # flag it as a risk instead of forcing a weak target.
    if high60 > entry and high60 < target:
        risks.append(f"Recent 60-day resistance near {high60:.2f}")

    if risk_per_share <= 0:
        score -= 30
        risks.append("Invalid stop distance")
    else:
        rr = (target - entry) / risk_per_share
        if rr >= 2:
            score += 15
            reasons.append("Risk/reward is at least 2R")
        elif rr < 1.5:
            score -= 15
            risks.append("Risk/reward is below 1.5R")

    if atr and price and atr / price > 0.06:
        score -= 10
        risks.append("Volatility is elevated; reduce size")

    score = int(max(0, min(100, score)))
    if score >= 80:
        recommendation = "READY"
        reason = "Professional-style setup is actionable if it fits your portfolio risk."
    elif score >= 60:
        recommendation = "REVIEW"
        reason = "Setup is workable, but wait for confirmation or reduce size."
    else:
        recommendation = "WAIT"
        reason = "Setup quality is not strong enough yet."

    return {
        "ticker": ticker,
        "valid": True,
        "recommendation": recommendation,
        "confidence": score,
        "entry": entry,
        "stop": stop,
        "target": target,
        "current_price": price,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "atr": atr,
        "high20": high20,
        "low20": low20,
        "high60": high60,
        "low60": low60,
        "setup_type": setup_type,
        "trend": trend,
        "momentum": momentum,
        "reason": reason,
        "reasons": reasons[:5],
        "risks": risks[:5],
    }


def build_trade_plan(ticker, entry, stop, target, account_size, cash_available, risk_pct, max_position_pct):
    ticker = (ticker or "").upper().strip()
    entry = float(entry or 0)
    stop = float(stop or 0)
    target = float(target or 0)
    account_size = float(account_size or 0)
    cash_available = float(cash_available or 0)
    risk_pct = float(risk_pct or 0)
    max_position_pct = float(max_position_pct or 0)

    risk_budget = account_size * risk_pct / 100
    max_position_value = account_size * max_position_pct / 100
    risk_per_share = max(entry - stop, 0)
    reward_per_share = max(target - entry, 0)

    if entry <= 0:
        status = "INVALID"
        note = "Entry price must be greater than zero."
        shares = 0
    elif risk_per_share <= 0:
        status = "INVALID"
        note = "Stop loss must be below entry for a long trade."
        shares = 0
    else:
        shares_by_risk = int(risk_budget // risk_per_share)
        shares_by_cash = int(cash_available // entry) if cash_available > 0 else shares_by_risk
        shares_by_size = int(max_position_value // entry) if max_position_value > 0 else shares_by_risk
        shares = max(0, min(shares_by_risk, shares_by_cash, shares_by_size))

        rr = reward_per_share / risk_per_share if risk_per_share else 0
        if shares <= 0:
            status = "WAIT"
            note = "Not enough cash or risk budget for this setup."
        elif rr < 1.5:
            status = "LOW R/R"
            note = "Risk/reward is below 1.5R. Consider waiting for a better entry or target."
        elif rr >= 2:
            status = "GOOD"
            note = "Trade setup has strong risk/reward and position size."
        else:
            status = "OK"
            note = "Trade setup is acceptable, but risk/reward is not very strong."

    capital_needed = shares * entry
    max_loss = shares * risk_per_share
    max_gain = shares * reward_per_share
    risk_reward = reward_per_share / risk_per_share if risk_per_share else 0
    position_pct = capital_needed / account_size * 100 if account_size else 0

    status_color = "green"
    if status in ["INVALID", "LOW R/R"]:
        status_color = "red"
    elif status in ["WAIT", "OK"]:
        status_color = "yellow"

    return {
        "ticker": ticker,
        "suggested_shares": shares,
        "capital_needed": round(capital_needed, 2),
        "max_loss": round(max_loss, 2),
        "max_gain": round(max_gain, 2),
        "risk_per_share": round(risk_per_share, 2),
        "reward_per_share": round(reward_per_share, 2),
        "risk_reward": round(risk_reward, 2),
        "position_pct": round(position_pct, 2),
        "status": status,
        "status_color": status_color,
        "note": note,
    }


def trade_score(plan: dict, current_weight: float = 0.0, cash_weight: float = 0.0, setup: dict | None = None) -> dict:
    """Rule-based trade assistant. No LLM, no order execution."""
    rr = float(plan.get("risk_reward", 0) or 0)
    shares = int(plan.get("suggested_shares", 0) or 0)
    position_pct = float(plan.get("position_pct", 0) or 0)
    status = plan.get("status", "")

    score = 0
    reasons = []
    risks = []

    if setup:
        score += int(float(setup.get("confidence", 0) or 0) * 0.45)
        reasons.extend(setup.get("reasons", [])[:3])
        risks.extend(setup.get("risks", [])[:3])
    else:
        score += 30

    if shares > 0:
        score += 15
        reasons.append("Position size is valid")
    else:
        risks.append("No shares suggested because cash or risk budget is too low")

    if rr >= 2.0:
        score += 20
        reasons.append("Risk/reward is strong (2R or better)")
    elif rr >= 1.5:
        score += 12
        reasons.append("Risk/reward is acceptable")
    else:
        risks.append("Risk/reward is below 1.5R")

    if 0 < position_pct <= 15:
        score += 10
        reasons.append("Position size is within limit")
    elif position_pct > 15:
        risks.append("Position size is too large for the portfolio")

    if current_weight < 20:
        score += 5
    else:
        risks.append("Portfolio already has high exposure to this ticker")

    if cash_weight < 5:
        risks.append("Cash buffer is low")
    else:
        score += 5

    if status in ["INVALID", "WAIT", "LOW R/R"]:
        risks.append(plan.get("note", "Setup needs review"))

    score = int(max(0, min(100, score)))
    if score >= 80:
        recommendation = "READY"
        color = "green"
        summary = "Setup is actionable if market conditions remain supportive."
    elif score >= 60:
        recommendation = "REVIEW"
        color = "yellow"
        summary = "Setup is close, but review price confirmation and position size."
    else:
        recommendation = "WAIT"
        color = "red"
        summary = "Setup is not ready. Wait for better entry, trend, or risk/reward."

    return {
        "score": score,
        "recommendation": recommendation,
        "color": color,
        "summary": summary,
        "reasons": reasons[:5],
        "risks": risks[:5],
    }


def checklist_readiness(plan: dict, checklist_items: list[bool]) -> dict:
    analysis = trade_score(plan)
    return {
        "score": int(sum(bool(x) for x in checklist_items)),
        "total": len(checklist_items),
        "readiness": analysis["recommendation"],
        "color": analysis["color"],
        "note": analysis["summary"],
    }


def save_trade_plan(ticker, entry, stop, target, plan, note="", checklist_score=0, readiness="", thesis="", exit_plan=""):
    """Save a planned trade to the journal. This does not execute orders."""
    ticker = (ticker or "").upper().strip()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO trade_journal (
                created_at, ticker, status, entry, stop, target, shares,
                capital_needed, max_loss, max_gain, risk_reward, setup_status,
                checklist_score, readiness, thesis, exit_plan, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                ticker,
                "Planned",
                float(entry or 0),
                float(stop or 0),
                float(target or 0),
                float(plan.get("suggested_shares", 0)),
                float(plan.get("capital_needed", 0)),
                float(plan.get("max_loss", 0)),
                float(plan.get("max_gain", 0)),
                float(plan.get("risk_reward", 0)),
                plan.get("status", ""),
                int(checklist_score or 0),
                readiness or "",
                thesis or "",
                exit_plan or "",
                note or plan.get("note", ""),
            ),
        )


def get_trade_journal(limit=None) -> pd.DataFrame:
    q = """
        SELECT id, created_at, ticker, status, entry, stop, target, shares,
               capital_needed, max_loss, max_gain, risk_reward, setup_status,
               checklist_score, readiness, thesis, exit_plan, note
        FROM trade_journal
        ORDER BY id DESC
    """
    if limit:
        q += f" LIMIT {int(limit)}"
    with connect() as conn:
        return pd.read_sql_query(q, conn)


def update_trade_status(trade_id, status):
    with connect() as conn:
        conn.execute("UPDATE trade_journal SET status=? WHERE id=?", (status, int(trade_id)))


def delete_trade_plan(trade_id):
    with connect() as conn:
        conn.execute("DELETE FROM trade_journal WHERE id=?", (int(trade_id),))
