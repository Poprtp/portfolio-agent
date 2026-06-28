from __future__ import annotations

import pandas as pd


def risk_score(portfolio: pd.DataFrame) -> tuple[int, list[str]]:
    score = 0
    notes: list[str] = []
    if portfolio.empty:
        return 0, ["No holdings found."]

    max_weight = float(portfolio["weight"].max())
    top = portfolio.sort_values("weight", ascending=False).iloc[0]
    if max_weight > 50:
        score += 40
        notes.append(f"High concentration: {top['ticker']} is {max_weight:.1f}% of portfolio.")
    elif max_weight > 35:
        score += 25
        notes.append(f"Moderate concentration: {top['ticker']} is {max_weight:.1f}% of portfolio.")

    income_weight = float(portfolio.loc[portfolio["asset_type"].str.contains("Income", case=False, na=False), "weight"].sum())
    growth_weight = float(portfolio.loc[portfolio["asset_type"].str.contains("Growth", case=False, na=False), "weight"].sum())
    cash_weight = float(portfolio.loc[portfolio["ticker"] == "CASH", "weight"].sum())

    if income_weight > 45:
        score += 15
        notes.append(f"Income ETF exposure is high at {income_weight:.1f}%; upside may be capped.")
    if growth_weight > 70:
        score += 20
        notes.append(f"Growth exposure is high at {growth_weight:.1f}%; expect larger drawdowns.")
    if cash_weight < 5:
        score += 10
        notes.append("Cash buffer is low; limited ability to buy market dips.")

    if not notes:
        notes.append("Portfolio risk looks balanced based on current allocation rules.")
    return min(score, 100), notes


def action_label(row: pd.Series) -> str:
    if row["ticker"] == "CASH":
        return "Reserve"
    if row["drift"] > 10:
        return "Stop adding / Trim only if needed"
    if row["drift"] < -10:
        return "Add gradually"
    return "Hold"
