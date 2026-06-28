from datetime import datetime

import pandas as pd
import yfinance as yf

from services.database import connect


TRADER_MINDSET = {
    "profile": "Professional trader with 15+ years of experience",
    "principles": [
        "Capital preservation comes first.",
        "No trade without a clear entry, stop, target, and at least acceptable risk/reward.",
        "Prefer trades aligned with the primary trend.",
        "Avoid chasing extended moves; wait for pullbacks or clean breakouts.",
        "Setup quality and execution feasibility are separate decisions.",
    ],
}


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


def _base_setup(ticker: str, reason: str, risk: str = "") -> dict:
    return {
        "ticker": ticker,
        "valid": False,
        "recommendation": "WAIT",
        "confidence": 0,
        "entry": 0.0,
        "stop": 0.0,
        "target": 0.0,
        "current_price": 0.0,
        "ma20": 0.0,
        "ma50": 0.0,
        "ma200": 0.0,
        "atr": 0.0,
        "high20": 0.0,
        "low20": 0.0,
        "high60": 0.0,
        "low60": 0.0,
        "setup_type": "No clean setup",
        "trend": "Unknown",
        "momentum": "Unknown",
        "reason": reason,
        "reasons": [],
        "risks": [risk or reason],
        "trade_rule": "Stand aside until the setup is measurable.",
    }


def professional_trade_setup(ticker: str) -> dict:
    """Create a long-only trade setup using a disciplined professional trader framework.

    The engine behaves like a 15+ year discretionary trader:
    - Trend first, then entry quality.
    - Never chase if price is extended.
    - Entry, stop, and target are always tied to ATR / support / resistance.
    - If the trade is not ready, it still gives a conditional level to watch.
    """
    ticker = (ticker or "").upper().strip()
    if not ticker:
        return _base_setup("", "Enter a ticker first.", "No ticker entered")

    try:
        data = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
    except Exception as exc:
        return _base_setup(ticker, f"Could not load market data: {exc}", "Market data unavailable")

    data = data.dropna(subset=["Close", "High", "Low"])
    if data.empty or len(data) < 80:
        return _base_setup(ticker, "Not enough price history to create a reliable setup.", "Insufficient price history")

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

    reasons: list[str] = []
    risks: list[str] = []
    score = 50

    strong_uptrend = price > ma20 > ma50 >= ma200
    uptrend = price > ma50 and ma50 >= ma200
    downtrend = price < ma50 or ma50 < ma200
    near_breakout = atr > 0 and price >= high20 - 0.35 * atr
    extended = atr > 0 and price > ma20 + 1.4 * atr
    deep_pullback = price < ma20 and price > ma50 and ma50 >= ma200
    volatility_pct = atr / price if price else 0

    if strong_uptrend:
        trend = "Bullish"
        momentum = "Strong"
        score += 25
        reasons.append("Primary trend is bullish: price > MA20 > MA50 > MA200")
    elif uptrend:
        trend = "Bullish"
        momentum = "Moderate"
        score += 15
        reasons.append("Primary trend remains constructive above MA50")
    elif downtrend:
        trend = "Bearish / Defensive"
        momentum = "Weak"
        score -= 25
        risks.append("Primary trend is weak; professional traders avoid forcing longs")
    else:
        trend = "Neutral"
        momentum = "Mixed"
        score -= 5
        risks.append("Trend is mixed; wait for confirmation")

    if volatility_pct > 0.065:
        score -= 10
        risks.append("ATR volatility is high; reduce size or wait")
    elif 0 < volatility_pct <= 0.045:
        score += 5
        reasons.append("Volatility is controlled enough for defined risk")

    # Professional level generation: setup-specific, not random target guessing.
    if strong_uptrend and not extended:
        setup_type = "Trend continuation"
        recommendation = "READY"
        entry = price
        stop = min(low20, entry - 1.4 * atr) if atr else low20
        trade_rule = "Actionable only while price holds above the short-term trend. Do not average down below stop."
        reasons.append("Not extended from MA20; continuation entry is acceptable")
    elif strong_uptrend and extended:
        setup_type = "Pullback entry"
        recommendation = "REVIEW"
        entry = max(ma20, price - 1.1 * atr) if atr else ma20
        stop = entry - 1.6 * atr if atr else low20
        trade_rule = "Do not chase. Place this on watch and wait for a pullback into the entry zone."
        score -= 10
        risks.append("Price is extended; chasing here has poor expectancy")
    elif deep_pullback:
        setup_type = "Controlled pullback"
        recommendation = "REVIEW"
        entry = price
        stop = min(low20, ma50 - 0.5 * atr) if atr else low20
        trade_rule = "Only valid if price stabilizes and closes back above MA20."
        score += 5
        reasons.append("Pullback remains above MA50, which can offer defined risk")
    elif near_breakout and not downtrend:
        setup_type = "Breakout confirmation"
        recommendation = "REVIEW"
        entry = round(high20 + max(0.05 * atr, price * 0.002), 2) if atr else round(high20 * 1.005, 2)
        stop = min(ma20, entry - 1.7 * atr) if atr else ma20
        trade_rule = "Use buy-stop logic only if breakout confirms with strength; avoid false breakouts."
        score += 8
        reasons.append("Price is near a short-term breakout level")
    else:
        setup_type = "Wait for confirmation"
        recommendation = "WAIT"
        if downtrend:
            entry = round(max(ma50, high20 + 0.1 * atr), 2) if atr else high20
            stop = entry - 1.8 * atr if atr else low20
        else:
            entry = round(high20 + max(0.05 * atr, price * 0.002), 2) if atr else round(high20 * 1.005, 2)
            stop = min(low20, entry - 1.8 * atr) if atr else low20
        trade_rule = "No trade now. Use the suggested level as a trigger, not an immediate entry."
        risks.append("No professional-quality long setup yet")

    entry = round(max(float(entry), 0.0), 2)
    stop = round(max(float(stop), 0.01), 2)
    if stop >= entry and atr:
        stop = round(max(0.01, entry - 1.6 * atr), 2)

    risk_per_share = max(entry - stop, 0)
    if risk_per_share <= 0:
        target = round(high60, 2)
        score -= 30
        risks.append("Invalid stop distance")
    else:
        target = round(entry + risk_per_share * 2.2, 2)
        rr = (target - entry) / risk_per_share
        if rr >= 2.0:
            score += 12
            reasons.append("Setup offers at least 2R planned reward")
        else:
            score -= 10
            risks.append("Risk/reward is not attractive enough")

    if high60 > entry and high60 < target:
        risks.append(f"Nearby 60-day resistance around {high60:.2f}; consider partial profit there")

    score = int(max(0, min(100, score)))
    if score >= 78 and recommendation != "WAIT":
        final_rec = "READY"
        reason = "Professional-quality setup: trend, level, and risk/reward are aligned."
    elif score >= 58 and recommendation != "WAIT":
        final_rec = "REVIEW"
        reason = "Setup is workable but needs confirmation, cleaner entry, or smaller size."
    else:
        final_rec = "WAIT"
        reason = "Stand aside. Better traders wait for the setup to come to them."

    return {
        "ticker": ticker,
        "valid": True,
        "recommendation": final_rec,
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
        "trade_rule": trade_rule,
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
        execution_status = "INVALID"
        note = "Entry price must be greater than zero."
        shares_by_risk = shares_by_cash = shares_by_size = shares = 0
    elif risk_per_share <= 0:
        execution_status = "INVALID"
        note = "Stop loss must be below entry for a long trade."
        shares_by_risk = shares_by_cash = shares_by_size = shares = 0
    else:
        shares_by_risk = int(risk_budget // risk_per_share)
        shares_by_cash = int(cash_available // entry) if cash_available > 0 else 0
        shares_by_size = int(max_position_value // entry) if max_position_value > 0 else shares_by_risk
        shares = max(0, min(shares_by_risk, shares_by_cash, shares_by_size))

        rr = reward_per_share / risk_per_share if risk_per_share else 0
        if shares <= 0 and shares_by_risk > 0:
            execution_status = "NO CASH"
            note = "Setup may be valid, but available cash is not enough for one share."
        elif shares <= 0:
            execution_status = "NO SIZE"
            note = "Risk budget or max position limit is too small for this setup."
        elif rr < 1.5:
            execution_status = "LOW R/R"
            note = "Risk/reward is below 1.5R. Wait for a better entry or target."
        elif rr >= 2:
            execution_status = "EXECUTABLE"
            note = "Execution constraints are acceptable."
        else:
            execution_status = "SMALL SIZE"
            note = "Acceptable, but the setup does not offer strong asymmetry."

    capital_needed = shares * entry
    max_loss = shares * risk_per_share
    max_gain = shares * reward_per_share
    risk_reward = reward_per_share / risk_per_share if risk_per_share else 0
    position_pct = capital_needed / account_size * 100 if account_size else 0

    status_color = "green" if execution_status == "EXECUTABLE" else "yellow"
    if execution_status in ["INVALID", "LOW R/R"]:
        status_color = "red"

    return {
        "ticker": ticker,
        "suggested_shares": shares,
        "shares_by_risk": shares_by_risk,
        "shares_by_cash": shares_by_cash,
        "shares_by_size": shares_by_size,
        "capital_needed": round(capital_needed, 2),
        "max_loss": round(max_loss, 2),
        "max_gain": round(max_gain, 2),
        "risk_per_share": round(risk_per_share, 2),
        "reward_per_share": round(reward_per_share, 2),
        "risk_reward": round(risk_reward, 2),
        "position_pct": round(position_pct, 2),
        "status": execution_status,
        "status_color": status_color,
        "note": note,
    }


def trade_score(plan: dict, current_weight: float = 0.0, cash_weight: float = 0.0, setup: dict | None = None) -> dict:
    """Blend setup quality with execution feasibility without confusing the two."""
    rr = float(plan.get("risk_reward", 0) or 0)
    shares = int(plan.get("suggested_shares", 0) or 0)
    position_pct = float(plan.get("position_pct", 0) or 0)
    execution_status = plan.get("status", "")
    setup_score = int(float(setup.get("confidence", 0) if setup else 0))
    setup_rec = setup.get("recommendation", "WAIT") if setup else "WAIT"

    execution_score = 0
    reasons = []
    risks = []

    if setup:
        reasons.extend(setup.get("reasons", [])[:3])
        risks.extend(setup.get("risks", [])[:3])

    if shares > 0:
        execution_score += 25
        reasons.append("Position size is executable within current constraints")
    else:
        risks.append(plan.get("note", "Execution is not feasible yet"))

    if rr >= 2.0:
        execution_score += 25
        reasons.append("Risk/reward is professional-grade (2R or better)")
    elif rr >= 1.5:
        execution_score += 15
        reasons.append("Risk/reward is acceptable but not exceptional")
    else:
        risks.append("Risk/reward is below professional threshold")

    if 0 < position_pct <= 15:
        execution_score += 20
        reasons.append("Position size is within max allocation limit")
    elif position_pct > 15:
        risks.append("Position size is too large for the portfolio")

    if current_weight >= 20:
        risks.append("Portfolio already has high exposure to this ticker")
    else:
        execution_score += 10

    if cash_weight < 5:
        risks.append("Cash buffer is low; new trades require extra discipline")
    else:
        execution_score += 10

    if execution_status in ["INVALID", "LOW R/R"]:
        risks.append(plan.get("note", "Execution needs review"))

    execution_score = int(max(0, min(100, execution_score)))
    score = int(max(0, min(100, round(setup_score * 0.7 + execution_score * 0.3))))

    if setup_rec == "READY" and execution_status == "EXECUTABLE" and score >= 75:
        recommendation = "READY"
        color = "green"
        summary = "Setup and execution are aligned. Trade is actionable if market confirms."
    elif setup_rec in ["READY", "REVIEW"] and execution_status in ["NO CASH", "NO SIZE"]:
        recommendation = "NO CASH"
        color = "yellow"
        summary = "Setup may be useful, but execution is blocked by cash or size limits."
    elif setup_rec in ["READY", "REVIEW"] and score >= 55:
        recommendation = "REVIEW"
        color = "yellow"
        summary = "Setup is close, but wait for confirmation or adjust size."
    else:
        recommendation = "WAIT"
        color = "red"
        summary = "Professional discipline says wait. Setup or execution is not good enough."

    return {
        "score": score,
        "setup_score": setup_score,
        "execution_score": execution_score,
        "setup_recommendation": setup_rec,
        "execution_status": execution_status,
        "recommendation": recommendation,
        "color": color,
        "summary": summary,
        "reasons": list(dict.fromkeys(reasons))[:5],
        "risks": list(dict.fromkeys(risks))[:5],
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
