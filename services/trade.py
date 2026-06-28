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
            note = "Trade setup has acceptable risk/reward and position size."
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
