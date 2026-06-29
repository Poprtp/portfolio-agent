import os
from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from services.database import connect


def load_alert_watchlist(path: str = "config/alert_watchlist.txt") -> int:
    """Load scheduled-alert symbols from config/alert_watchlist.txt into SQLite.
    This is used by GitHub Actions because the Streamlit Cloud SQLite file is not shared with Actions.
    """
    if not os.path.exists(path):
        return 0
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            ticker = line.split("#", 1)[0].strip().split()[0].upper()
            if ticker:
                rows.append((ticker, ticker, 3))
    if not rows:
        return 0
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO watchlist (ticker, name, conviction)
            VALUES (?, ?, ?)
            ON CONFLICT(ticker) DO NOTHING
            """,
            rows,
        )
    return len(rows)


def alert_candidates(desk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if desk is None or desk.empty:
        return pd.DataFrame(), pd.DataFrame()
    ready = desk[desk["Decision"].astype(str).str.upper() == "READY"].copy()
    review = desk[desk["Decision"].astype(str).str.upper() == "REVIEW"].copy()
    if not review.empty:
        setup = review.get("Setup", "").astype(str).str.lower()
        review = review[(review["Score"].fillna(0) >= 68) | setup.str.contains("pullback|continuation|breakout", regex=True)]
    return ready.sort_values("Score", ascending=False), review.sort_values("Score", ascending=False)


def _line(row) -> str:
    ticker = str(row.get("Ticker", ""))
    decision = str(row.get("Decision", ""))
    score = int(row.get("Score", 0) or 0)
    price = float(row.get("Price", 0) or 0)
    entry = float(row.get("Entry", 0) or 0)
    stop = float(row.get("Stop", 0) or 0)
    target = float(row.get("Target", 0) or 0)
    rr = row.get("R/R", 0)
    setup = str(row.get("Setup", ""))
    return f"• **{ticker}** — {decision} · Score {score}/100 · Price ${price:,.2f}\n  Trigger ${entry:,.2f} · Stop ${stop:,.2f} · Target ${target:,.2f} · R/R {rr}R\n  Setup: {setup}"


def build_discord_alert_message(desk: pd.DataFrame, run_label: str = "Scheduled scan", include_empty: bool = False) -> str | None:
    ready, review = alert_candidates(desk)
    now_bkk = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M BKK")
    now_ny = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M NY")

    if ready.empty and review.empty and not include_empty:
        return None

    lines = [
        "📈 **Portfolio OS Alert**",
        f"{run_label} · {now_bkk} · {now_ny}",
        "",
    ]
    if not ready.empty:
        lines.append("**READY — actionable setups**")
        for _, row in ready.head(5).iterrows():
            lines.append(_line(row))
        lines.append("")
    if not review.empty:
        lines.append("**REVIEW / Confirmation Watch**")
        for _, row in review.head(5).iterrows():
            lines.append(_line(row))
        lines.append("")
    if ready.empty and review.empty:
        lines.append("No READY or confirmation-quality REVIEW setups right now.")
        lines.append("")
    lines.append("Rule: ไม่ไล่ราคา ใช้เฉพาะ Buy Trigger + Stop ที่กำหนดไว้เท่านั้น")
    lines.append("Not financial advice. This is a planning alert, not an order.")
    message = "\n".join(lines)
    # Discord content limit is 2000 chars; keep it safe.
    return message[:1900]


def send_discord_message(webhook_url: str, content: str) -> Tuple[bool, str]:
    if not webhook_url:
        return False, "Missing DISCORD_WEBHOOK_URL"
    try:
        response = requests.post(webhook_url, json={"content": content}, timeout=15)
        if 200 <= response.status_code < 300:
            return True, "sent"
        return False, f"Discord returned {response.status_code}: {response.text[:200]}"
    except Exception as exc:
        return False, str(exc)


def send_discord_alert(webhook_url: str, desk: pd.DataFrame, run_label: str = "Manual test", include_empty: bool = True) -> Tuple[bool, str]:
    content = build_discord_alert_message(desk, run_label=run_label, include_empty=include_empty)
    if not content:
        return True, "No READY or confirmation candidates; no alert sent."
    return send_discord_message(webhook_url, content)
