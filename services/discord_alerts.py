import os
from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from services.database import connect


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def alert_filter_settings() -> dict:
    return {
        "ready_min_score": _env_float("ALERT_READY_MIN_SCORE", 80),
        "review_min_score": _env_float("ALERT_REVIEW_MIN_SCORE", 75),
        "max_trigger_distance_pct": _env_float("ALERT_MAX_TRIGGER_DISTANCE_PCT", 3.0),
        "min_rr": _env_float("ALERT_MIN_RR", 2.0),
    }


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


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _trigger_distance_pct(row) -> float:
    price = _safe_float(row.get("Price", 0))
    entry = _safe_float(row.get("Entry", 0))
    if price <= 0 or entry <= 0:
        return 999.0
    return abs(price - entry) / price * 100.0


def _rr(row) -> float:
    return _safe_float(row.get("R/R", 0))


def _score(row) -> int:
    try:
        return int(row.get("Score", 0) or 0)
    except Exception:
        return 0


def _is_confirmation_setup(row) -> bool:
    setup = str(row.get("Setup", "")).lower()
    reason = str(row.get("Reason", "")).lower()
    text = f"{setup} {reason}"
    confirmation_words = "pullback|continuation|breakout|actionable|confirmation|support|trend"
    return pd.Series([text]).str.contains(confirmation_words, regex=True).iloc[0]


def _quality_filter(df: pd.DataFrame, decision: str, min_score: float, settings: dict) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    rows = []
    for _, row in df.iterrows():
        dist = _trigger_distance_pct(row)
        rr = _rr(row)
        score = _score(row)
        setup_ok = True if decision == "READY" else _is_confirmation_setup(row)
        if (
            score >= min_score
            and rr >= settings["min_rr"]
            and dist <= settings["max_trigger_distance_pct"]
            and setup_ok
        ):
            copy = row.copy()
            copy["Trigger Distance %"] = round(dist, 2)
            rows.append(copy)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["Score", "Trigger Distance %"], ascending=[False, True])


def alert_candidates(desk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return only high-quality Discord alert candidates.

    Alert logic is intentionally stricter than the web Daily Desk to reduce noise:
    - READY must pass minimum score, R/R, and trigger-distance filters.
    - REVIEW must also look like a confirmation setup.
    - WAIT is never sent.
    """
    if desk is None or desk.empty:
        return pd.DataFrame(), pd.DataFrame()
    settings = alert_filter_settings()
    decisions = desk["Decision"].astype(str).str.upper()
    ready_raw = desk[decisions == "READY"].copy()
    review_raw = desk[decisions == "REVIEW"].copy()
    ready = _quality_filter(ready_raw, "READY", settings["ready_min_score"], settings)
    review = _quality_filter(review_raw, "REVIEW", settings["review_min_score"], settings)
    return ready, review


def _line(row) -> str:
    ticker = str(row.get("Ticker", ""))
    decision = str(row.get("Decision", ""))
    score = int(row.get("Score", 0) or 0)
    price = _safe_float(row.get("Price", 0))
    entry = _safe_float(row.get("Entry", 0))
    stop = _safe_float(row.get("Stop", 0))
    target = _safe_float(row.get("Target", 0))
    rr = _safe_float(row.get("R/R", 0))
    setup = str(row.get("Setup", ""))
    dist = _safe_float(row.get("Trigger Distance %", _trigger_distance_pct(row)))
    return (
        f"• **{ticker}** — {decision} · Score {score}/100 · Near trigger {dist:.1f}%\n"
        f"  Price ${price:,.2f} · Trigger ${entry:,.2f} · Stop ${stop:,.2f} · Target ${target:,.2f} · R/R {rr:.1f}R\n"
        f"  Setup: {setup}"
    )


def build_discord_alert_message(desk: pd.DataFrame, run_label: str = "Scheduled scan", include_empty: bool = False) -> str | None:
    ready, review = alert_candidates(desk)
    settings = alert_filter_settings()
    now_bkk = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M BKK")
    now_ny = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M NY")

    if ready.empty and review.empty and not include_empty:
        return None

    lines = [
        "📈 **Portfolio OS Alert — Quality Filter**",
        f"{run_label} · {now_bkk} · {now_ny}",
        f"Filter: READY ≥{settings['ready_min_score']:.0f}, REVIEW ≥{settings['review_min_score']:.0f}, near trigger ≤{settings['max_trigger_distance_pct']:.1f}%, R/R ≥{settings['min_rr']:.1f}R",
        "",
    ]
    if not ready.empty:
        lines.append("**READY — actionable now**")
        for _, row in ready.head(5).iterrows():
            lines.append(_line(row))
        lines.append("")
    if not review.empty:
        lines.append("**REVIEW — confirmation watch**")
        for _, row in review.head(5).iterrows():
            lines.append(_line(row))
        lines.append("")
    if ready.empty and review.empty:
        lines.append("No high-quality READY or confirmation REVIEW setups right now.")
        lines.append("This means the filter blocked noisy / far-from-trigger setups.")
        lines.append("")
    lines.append("Rule: ไม่ไล่ราคา ใช้เฉพาะ Buy Trigger + Stop ที่กำหนดไว้เท่านั้น")
    lines.append("Not financial advice. This is a planning alert, not an order.")
    message = "\n".join(lines)
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
        return True, "No high-quality READY or confirmation REVIEW candidates; no alert sent."
    return send_discord_message(webhook_url, content)
