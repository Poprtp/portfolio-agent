import json
from typing import Optional

import pandas as pd


def _desk_context(desk: pd.DataFrame, holdings: pd.DataFrame, summary: dict) -> dict:
    focus = []
    if desk is not None and not desk.empty:
        for _, r in desk.head(6).iterrows():
            focus.append(
                {
                    "ticker": r.get("Ticker"),
                    "decision": r.get("Decision"),
                    "score": int(r.get("Score", 0) or 0),
                    "price": float(r.get("Price", 0) or 0),
                    "entry": float(r.get("Entry", 0) or 0),
                    "stop": float(r.get("Stop", 0) or 0),
                    "target": float(r.get("Target", 0) or 0),
                    "setup": r.get("Setup"),
                    "business": r.get("Business"),
                    "growth": r.get("Growth"),
                    "profit": r.get("Profit"),
                    "valuation": r.get("Valuation"),
                }
            )
    positions = []
    if holdings is not None and not holdings.empty:
        for _, r in holdings.head(8).iterrows():
            positions.append(
                {
                    "ticker": r.get("ticker"),
                    "weight": float(r.get("weight", 0) or 0),
                    "pnl_pct": float(r.get("gain_loss_pct", 0) or 0),
                }
            )
    return {"summary": summary, "desk": focus, "holdings": positions}


def rule_based_advisor(desk: pd.DataFrame, holdings: pd.DataFrame, summary: dict) -> str:
    if desk is None or desk.empty:
        return "No watchlist yet. Add 3–8 tickers, then refresh."

    ready = desk[desk["Decision"] == "READY"]
    review = desk[desk["Decision"] == "REVIEW"]
    best = ready.iloc[0] if not ready.empty else review.iloc[0] if not review.empty else desk.iloc[0]

    lines = []
    if best["Decision"] == "READY":
        lines.append(f"Focus: {best['Ticker']} is the cleanest actionable setup today.")
    elif best["Decision"] == "REVIEW":
        lines.append(f"Focus: {best['Ticker']} is worth watching, but wait for confirmation.")
    else:
        lines.append("Focus: no clean buy setup. Waiting is the professional action.")

    if holdings is not None and not holdings.empty:
        top = holdings.iloc[0]
        if float(top.get("weight", 0) or 0) > 70:
            lines.append(f"Risk: portfolio is highly concentrated in {top['ticker']}. Avoid adding correlated risk.")
        losers = holdings[holdings["gain_loss_pct"] < -15]
        if not losers.empty:
            row = losers.iloc[0]
            lines.append(f"Review: {row['ticker']} is down {row['gain_loss_pct']:.1f}%; check thesis and stop plan.")

    lines.append("Rule: do not chase price. Buy only near trigger with a defined stop.")
    return "\n".join(lines[:4])


def ai_advisor(desk: pd.DataFrame, holdings: pd.DataFrame, summary: dict, api_key: Optional[str] = None) -> str:
    """Optional GPT advisor. Falls back to rule-based advisor without an API key."""
    if not api_key:
        return rule_based_advisor(desk, holdings, summary)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        context = _desk_context(desk, holdings, summary)
        prompt = (
            "You are a professional stock trader with 15+ years of experience. "
            "Give a concise daily plan. Prioritize risk control, no chasing, clear trigger/stop/target. "
            "Do not promise returns. Output 3 short bullets only.\n\n"
            f"Context JSON:\n{json.dumps(context, ensure_ascii=False)}"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=220,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        return rule_based_advisor(desk, holdings, summary) + f"\nAI fallback active: {exc.__class__.__name__}."
