from datetime import datetime

import pandas as pd

from services.database import connect


def _calc_shares(entry: float, stop: float, portfolio_value: float, risk_pct: float = 1.0) -> int:
    risk = max(float(entry or 0) - float(stop or 0), 0)
    if risk <= 0 or portfolio_value <= 0:
        return 0
    risk_budget = portfolio_value * risk_pct / 100
    return max(0, int(risk_budget // risk))


def save_planned_trade(row: dict, portfolio_value: float, note: str = "") -> int:
    ticker = str(row.get("Ticker", "")).upper().strip()
    entry = float(row.get("Entry", 0) or 0)
    stop = float(row.get("Stop", 0) or 0)
    target = float(row.get("Target", 0) or 0)
    shares = _calc_shares(entry, stop, float(portfolio_value or 0), 1.0)
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO trade_journal (
                created_at, ticker, status, decision, score, entry, stop, target, shares, risk_reward, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                ticker,
                "Planned",
                str(row.get("Decision", "")),
                int(row.get("Score", 0) or 0),
                entry,
                stop,
                target,
                shares,
                float(row.get("R/R", 0) or 0),
                note or str(row.get("Reason", "")),
            ),
        )
        return int(cur.lastrowid)


def get_trade_journal(limit: int = 5) -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT id, created_at, ticker, status, decision, score, entry, stop, target, shares, risk_reward, note
            FROM trade_journal
            ORDER BY id DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
        )


def update_trade_status(trade_id: int, status: str):
    with connect() as conn:
        conn.execute("UPDATE trade_journal SET status=? WHERE id=?", (status, int(trade_id)))


def delete_trade(trade_id: int):
    with connect() as conn:
        conn.execute("DELETE FROM trade_journal WHERE id=?", (int(trade_id),))
