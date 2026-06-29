import pandas as pd


def decision_alerts(desk: pd.DataFrame, holdings: pd.DataFrame) -> list[str]:
    alerts: list[str] = []

    if desk is not None and not desk.empty:
        for _, r in desk.head(8).iterrows():
            ticker = str(r.get("Ticker", ""))
            decision = str(r.get("Decision", ""))
            price = float(r.get("Price", 0) or 0)
            entry = float(r.get("Entry", 0) or 0)
            stop = float(r.get("Stop", 0) or 0)
            if price <= 0 or entry <= 0:
                continue
            distance = (price - entry) / entry
            if decision in ["READY", "REVIEW"] and abs(distance) <= 0.02:
                alerts.append(f"{ticker}: near Buy Trigger ({distance*100:+.1f}%)")
            elif decision == "REVIEW" and price < entry and abs(distance) <= 0.05:
                alerts.append(f"{ticker}: close below trigger, wait for reclaim")
            if stop > 0 and price <= stop * 1.03:
                alerts.append(f"{ticker}: near stop zone; avoid adding")

    if holdings is not None and not holdings.empty:
        top = holdings.iloc[0]
        if float(top.get("weight", 0) or 0) > 70:
            alerts.append(f"Portfolio: {top['ticker']} is over 70% of holdings")
        losers = holdings[holdings["gain_loss_pct"] < -15]
        if not losers.empty:
            row = losers.iloc[0]
            alerts.append(f"Risk: review {row['ticker']} loss ({row['gain_loss_pct']:.1f}%)")

    if not alerts:
        alerts.append("No urgent alerts. Follow the plan and avoid forced trades.")
    return alerts[:5]
