from datetime import date, datetime, timedelta

import pandas as pd

from services.database import connect
from services.market import fetch_price


def _safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _ensure_history_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            ticker TEXT DEFAULT '',
            decision TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            technical_score INTEGER DEFAULT 0,
            homework_score INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            entry REAL DEFAULT 0,
            stop REAL DEFAULT 0,
            target REAL DEFAULT 0,
            risk_reward REAL DEFAULT 0,
            setup TEXT DEFAULT '',
            reason TEXT DEFAULT ''
        )
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(decision_history)").fetchall()}
    defaults = {
        "snapshot_date": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''",
        "ticker": "TEXT DEFAULT ''",
        "decision": "TEXT DEFAULT ''",
        "score": "INTEGER DEFAULT 0",
        "technical_score": "INTEGER DEFAULT 0",
        "homework_score": "INTEGER DEFAULT 0",
        "price": "REAL DEFAULT 0",
        "entry": "REAL DEFAULT 0",
        "stop": "REAL DEFAULT 0",
        "target": "REAL DEFAULT 0",
        "risk_reward": "REAL DEFAULT 0",
        "setup": "TEXT DEFAULT ''",
        "reason": "TEXT DEFAULT ''",
    }
    for col, spec in defaults.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE decision_history ADD COLUMN {col} {spec}")


def save_daily_snapshot(desk: pd.DataFrame) -> int:
    """Save today's desk calls safely. Re-running replaces today's snapshot."""
    if desk is None or desk.empty:
        return 0
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for _, r in desk.iterrows():
        ticker = str(r.get("Ticker", "")).upper().strip()
        if not ticker:
            continue
        rows.append(
            (
                today,
                now,
                ticker,
                str(r.get("Decision", "")),
                _safe_int(r.get("Score", 0)),
                _safe_int(r.get("Technical Score", 0)),
                _safe_int(r.get("Homework Score", 0)),
                _safe_float(r.get("Price", 0)),
                _safe_float(r.get("Entry", 0)),
                _safe_float(r.get("Stop", 0)),
                _safe_float(r.get("Target", 0)),
                _safe_float(r.get("R/R", 0)),
                str(r.get("Setup", "")),
                str(r.get("Reason", "")),
            )
        )
    if not rows:
        return 0
    with connect() as conn:
        _ensure_history_schema(conn)
        # Avoid SQLite ON CONFLICT issues on older Streamlit databases that lack
        # the unique index from newer versions. One current-day snapshot per ticker.
        conn.execute("DELETE FROM decision_history WHERE snapshot_date=?", (today,))
        conn.executemany(
            """
            INSERT INTO decision_history (
                snapshot_date, created_at, ticker, decision, score, technical_score, homework_score,
                price, entry, stop, target, risk_reward, setup, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def get_recent_history(days: int = 7) -> pd.DataFrame:
    start = (date.today() - timedelta(days=days)).isoformat()
    with connect() as conn:
        _ensure_history_schema(conn)
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
        _ensure_history_schema(conn)
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
        then_price = _safe_float(r["then_price"], 0)
        returns.append(round((now_price - then_price) / then_price * 100, 2) if then_price else 0.0)
    df["now_price"] = now_prices
    df["return_pct"] = returns
    return df
