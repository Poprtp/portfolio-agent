from datetime import datetime

import pandas as pd

from services.database import connect


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


def trade_score(plan: dict, current_weight: float = 0.0, cash_weight: float = 0.0) -> dict:
    """Rule-based trade assistant. No LLM, no order execution."""
    rr = float(plan.get("risk_reward", 0) or 0)
    shares = int(plan.get("suggested_shares", 0) or 0)
    position_pct = float(plan.get("position_pct", 0) or 0)
    max_loss = float(plan.get("max_loss", 0) or 0)
    status = plan.get("status", "")

    score = 0
    reasons = []
    risks = []

    if shares > 0:
        score += 20
        reasons.append("Position size is valid")
    else:
        risks.append("No shares suggested because cash or risk budget is too low")

    if rr >= 2.0:
        score += 30
        reasons.append("Risk/reward is strong (2R or better)")
    elif rr >= 1.5:
        score += 20
        reasons.append("Risk/reward is acceptable")
    else:
        risks.append("Risk/reward is below 1.5R")

    if 0 < position_pct <= 15:
        score += 20
        reasons.append("Position size is within limit")
    elif position_pct > 15:
        risks.append("Position size is too large for the portfolio")

    if current_weight < 20:
        score += 10
        reasons.append("Existing exposure to this ticker is not excessive")
    else:
        risks.append("Portfolio already has high exposure to this ticker")

    if cash_weight >= 5:
        score += 10
        reasons.append("Cash buffer is acceptable")
    else:
        risks.append("Cash buffer is low")

    if status in ["GOOD", "OK"]:
        score += 10
    elif status in ["INVALID", "WAIT", "LOW R/R"]:
        risks.append(plan.get("note", "Setup needs review"))

    score = int(max(0, min(100, score)))
    if score >= 80:
        recommendation = "READY"
        color = "green"
        summary = "Setup is tradable if it matches your broader market view."
    elif score >= 60:
        recommendation = "REVIEW"
        color = "yellow"
        summary = "Setup is close, but review the risks before trading."
    else:
        recommendation = "WAIT"
        color = "red"
        summary = "Setup is not ready. Improve entry, stop, target, or cash/risk budget."

    return {
        "score": score,
        "recommendation": recommendation,
        "color": color,
        "summary": summary,
        "reasons": reasons[:4],
        "risks": risks[:4],
    }


def checklist_readiness(plan: dict, checklist_items: list[bool]) -> dict:
    # Kept for backwards compatibility with older saved journals.
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
