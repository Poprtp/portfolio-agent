import sqlite3
from pathlib import Path

DB_PATH = Path("data/portfolio.db")
DB_PATH.parent.mkdir(exist_ok=True)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def init_db():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS holdings (
                ticker TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                shares REAL DEFAULT 0,
                avg_cost REAL DEFAULT 0,
                current_price REAL DEFAULT 0,
                target_weight REAL DEFAULT 0,
                asset_type TEXT DEFAULT 'Stock',
                sector TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares REAL DEFAULT 0,
                price REAL DEFAULT 0,
                fees REAL DEFAULT 0,
                note TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                fair_value REAL DEFAULT 0,
                target_buy_price REAL DEFAULT 0,
                conviction INTEGER DEFAULT 3,
                note TEXT DEFAULT '',
                current_price REAL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                ticker TEXT NOT NULL,
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
                reason TEXT DEFAULT '',
                UNIQUE(snapshot_date, ticker)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                ticker TEXT NOT NULL,
                status TEXT DEFAULT 'Planned',
                decision TEXT DEFAULT '',
                score INTEGER DEFAULT 0,
                entry REAL DEFAULT 0,
                stop REAL DEFAULT 0,
                target REAL DEFAULT 0,
                shares REAL DEFAULT 0,
                risk_reward REAL DEFAULT 0,
                note TEXT DEFAULT ''
            )
            """
        )
        _migrate(conn)
        _seed_if_empty(conn)


def _migrate(conn):
    holding_defaults = {
        "name": "TEXT DEFAULT ''",
        "shares": "REAL DEFAULT 0",
        "avg_cost": "REAL DEFAULT 0",
        "current_price": "REAL DEFAULT 0",
        "target_weight": "REAL DEFAULT 0",
        "asset_type": "TEXT DEFAULT 'Stock'",
        "sector": "TEXT DEFAULT ''",
    }
    cols = _columns(conn, "holdings")
    for col, spec in holding_defaults.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE holdings ADD COLUMN {col} {spec}")

    tx_defaults = {"fees": "REAL DEFAULT 0", "note": "TEXT DEFAULT ''"}
    cols = _columns(conn, "transactions")
    for col, spec in tx_defaults.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE transactions ADD COLUMN {col} {spec}")

    watch_defaults = {
        "name": "TEXT DEFAULT ''",
        "fair_value": "REAL DEFAULT 0",
        "target_buy_price": "REAL DEFAULT 0",
        "conviction": "INTEGER DEFAULT 3",
        "note": "TEXT DEFAULT ''",
        "current_price": "REAL DEFAULT 0",
    }
    cols = _columns(conn, "watchlist")
    for col, spec in watch_defaults.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE watchlist ADD COLUMN {col} {spec}")

    decision_defaults = {
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
    cols = _columns(conn, "decision_history")
    for col, spec in decision_defaults.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE decision_history ADD COLUMN {col} {spec}")
    conn.execute(
        """
        DELETE FROM decision_history
        WHERE rowid NOT IN (
            SELECT MAX(rowid)
            FROM decision_history
            GROUP BY snapshot_date, ticker
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_decision_history_day_ticker ON decision_history(snapshot_date, ticker)")

    journal_defaults = {
        "decision": "TEXT DEFAULT ''",
        "score": "INTEGER DEFAULT 0",
        "risk_reward": "REAL DEFAULT 0",
        "note": "TEXT DEFAULT ''",
    }
    cols = _columns(conn, "trade_journal")
    for col, spec in journal_defaults.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE trade_journal ADD COLUMN {col} {spec}")


def _seed_if_empty(conn):
    hcount = conn.execute("SELECT COUNT(*) FROM holdings").fetchone()[0]
    if hcount == 0:
        conn.execute(
            """
            INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("QQQI", "NEOS Nasdaq-100 High Income ETF", 132, 52, 54.69, 35, "ETF", "Income ETF"),
        )

    wcount = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
    if wcount == 0:
        rows = [
            ("TSM", "Taiwan Semiconductor ADR", 5),
            ("MSFT", "Microsoft", 4),
            ("NVDA", "NVIDIA", 4),
            ("AVGO", "Broadcom", 4),
        ]
        conn.executemany(
            "INSERT INTO watchlist (ticker, name, conviction) VALUES (?, ?, ?)",
            rows,
        )


def set_setting(key: str, value: str):
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_setting(key: str, default: str = "") -> str:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default
