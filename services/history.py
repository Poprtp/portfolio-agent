from datetime import date, datetime, timedelta

import pandas as pd

from services.database import connect
from services.market import fetch_price


def save_daily_snapshot(desk: pd.DataFrame) -> int:
    """Save today's desk calls. Re-running updates the same date/ticker row."""
    if desk is None or desk.empty:
        return 0
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for _, r in desk.iterrows():
        rows.append(
            (
                today,
                now,
                str(r.get("Ticker", "")).upper(),
                str(r.get("Decision", "")),
                int(r.get("Score", 0) or 0),
                int(r.get("Technical Score", 0) or 0),
                int(r.get("Homework Score", 0) or 0),
                float(r.get("Price", 0) or 0),
                float(r.get("Entry", 0) or 0),
                float(r.get("Stop", 0) or 0),
                float(r.get("Target", 0) or 0),
                float(r.get("R/R", 0) or 0),
                str(r.get("Setup", "")),
                str(r.get("Reason", "")),
            )
        )
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO decision_history (
                snapshot_date, created_at, ticker, decision, score, technical_score, homework_score,
                price, entry, stop, target, risk_reward, setup, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_date, ticker) DO UPDATE SET
                created_at=excluded.created_at,
                decision=excluded.decision,
                score=excluded.score,
                technical_score=excluded.technical_score,
                homework_score=excluded.homework_score,
                price=excluded.price,
                entry=excluded.entry,
                stop=excluded.stop,
                target=excluded.target,
                risk_reward=excluded.risk_reward,
                setup=excluded.setup,
                reason=excluded.reason
            """,
            rows,
        )
    return len(rows)


def get_recent_history(days: int = 7) -> pd.DataFrame:
    start = (date.today() - timedelta(days=days)).isoformat()
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT snapshot_date, ticker, decision, score, price, entry, stop, target, risk_reward, setup
            FROM decision_history
            WHERE snapshot_date >= ?
            ORDER BY snapshot_date DESC, score DESC, ticker ASC
            """,
            conn,
            params=(start,),
        )


def get_last_call_performance(limit: int = 4) -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT h.snapshot_date, h.ticker, h.decision, h.score, h.price AS then_price,
                   h.entry, h.stop, h.target, h.setup
            FROM decision_history h
            JOIN (
                SELECT ticker, MAX(snapshot_date) AS max_date
                FROM decision_history
                WHERE snapshot_date < ?
                GROUP BY ticker
            ) latest
              ON h.ticker = latest.ticker AND h.snapshot_date = latest.max_date
            WHERE h.decision IN ('READY', 'REVIEW')
            ORDER BY h.score DESC, h.ticker ASC
            LIMIT ?
            """,
            conn,
            params=(date.today().isoformat(), limit),
        )
    if df.empty:
        return df
    now_prices = []
    returns = []
    for _, r in df.iterrows():
        now_price, _ = fetch_price(r["ticker"], r["then_price"])
        now_prices.append(now_price)
        then_price = float(r["then_price"] or 0)
        returns.append(round((now_price - then_price) / then_price * 100, 2) if then_price else 0.0)
    df["now_price"] = now_prices
    df["return_pct"] = returns
    return df
