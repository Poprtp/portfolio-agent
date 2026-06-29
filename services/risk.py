import math
from typing import Any

import pandas as pd


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _existing_position_value(ticker: str, holdings: pd.DataFrame | None) -> float:
    if holdings is None or holdings.empty or "ticker" not in holdings.columns:
        return 0.0
    match = holdings[holdings["ticker"].astype(str).str.upper() == str(ticker).upper()]
    if match.empty or "market_value" not in match.columns:
        return 0.0
    return _safe_float(match.iloc[0].get("market_value", 0))


def calculate_trade_risk(
    row: dict,
    portfolio_value: float,
    holdings: pd.DataFrame | None = None,
    risk_pct: float = 1.0,
    max_position_pct: float = 15.0,
) -> dict:
    """Position-sizing plan for a long trade.

    Professional default: risk first, then position size. READY only means the setup is worth
    reviewing; this function decides whether the trade size is acceptable.
    """
    ticker = str(row.get("Ticker", "")).upper().strip()
    decision = str(row.get("Decision", "WAIT")).upper().strip()
    entry = _safe_float(row.get("Entry", 0))
    stop = _safe_float(row.get("Stop", 0))
    target = _safe_float(row.get("Target", 0))
    price = _safe_float(row.get("Price", entry))
    portfolio_value = _safe_float(portfolio_value)
    risk_pct = max(_safe_float(risk_pct, 1.0), 0.01)
    max_position_pct = max(_safe_float(max_position_pct, 15.0), 1.0)

    risk_per_share = max(entry - stop, 0.0)
    reward_per_share = max(target - entry, 0.0)
    rr = reward_per_share / risk_per_share if risk_per_share > 0 else 0.0
    risk_budget = portfolio_value * risk_pct / 100 if portfolio_value > 0 else 0.0
    max_position_value = portfolio_value * max_position_pct / 100 if portfolio_value > 0 else 0.0
    existing_value = _existing_position_value(ticker, holdings)
    remaining_position_value = max(max_position_value - existing_value, 0.0)

    shares_by_risk = math.floor(risk_budget / risk_per_share) if risk_per_share > 0 else 0
    shares_by_position = math.floor(remaining_position_value / entry) if entry > 0 else 0
    suggested_shares = max(0, min(shares_by_risk, shares_by_position))

    capital_needed = suggested_shares * entry
    max_loss = suggested_shares * risk_per_share
    expected_profit = suggested_shares * reward_per_share
    position_pct = (capital_needed / portfolio_value * 100) if portfolio_value > 0 else 0.0
    max_loss_pct = (max_loss / portfolio_value * 100) if portfolio_value > 0 else 0.0
    stop_distance_pct = (risk_per_share / entry * 100) if entry > 0 else 0.0
    trigger_distance_pct = abs(price - entry) / price * 100 if price > 0 and entry > 0 else 999.0

    status = "OK"
    note = "Risk fits the default professional sizing rules."
    if decision == "WAIT":
        status = "WAIT"
        note = "Setup is not clean enough; risk sizing is only a reference."
    elif suggested_shares <= 0:
        status = "SKIP"
        if remaining_position_value <= 0 and existing_value > 0:
            note = f"Already near the max position limit for {ticker}."
        elif risk_per_share <= 0:
            note = "Invalid Entry/Stop; risk cannot be calculated."
        else:
            note = "Position size would be too small under the current risk rules."
    elif stop_distance_pct > 12:
        status = "REDUCE"
        note = "Stop is wide; keep size small or wait for a tighter setup."
    elif trigger_distance_pct > 3:
        status = "WAIT PRICE"
        note = "Price is not close enough to Buy Trigger; avoid chasing."
    elif rr < 2:
        status = "REVIEW"
        note = "Risk/reward is below the preferred 2R threshold."

    return {
        "ticker": ticker,
        "status": status,
        "note": note,
        "risk_pct": risk_pct,
        "max_position_pct": max_position_pct,
        "risk_budget": round(risk_budget, 2),
        "suggested_shares": int(suggested_shares),
        "capital_needed": round(capital_needed, 2),
        "max_loss": round(max_loss, 2),
        "max_loss_pct": round(max_loss_pct, 2),
        "expected_profit": round(expected_profit, 2),
        "position_pct": round(position_pct, 2),
        "risk_per_share": round(risk_per_share, 2),
        "stop_distance_pct": round(stop_distance_pct, 2),
        "trigger_distance_pct": round(trigger_distance_pct, 2),
        "rr": round(rr, 2),
        "existing_value": round(existing_value, 2),
        "remaining_position_value": round(remaining_position_value, 2),
    }


def risk_note_for_journal(plan: dict) -> str:
    return (
        f"AI Risk Plan: {plan.get('status')} | "
        f"Suggested {plan.get('suggested_shares', 0)} shares | "
        f"Max loss ${plan.get('max_loss', 0):,.2f} ({plan.get('max_loss_pct', 0):.2f}%) | "
        f"Capital ${plan.get('capital_needed', 0):,.2f} | "
        f"{plan.get('note', '')}"
    )
