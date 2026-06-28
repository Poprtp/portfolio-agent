import sqlite3
from pathlib import Path

DB_PATH = Path("data/portfolio.db")
DB_PATH.parent.mkdir(exist_ok=True)


def connect():
    return sqlite3.connect(DB_PATH)


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
        _migrate_columns(conn)
        _seed_if_empty(conn)


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate_columns(conn):
    holding_cols = _columns(conn, "holdings")
    holding_defaults = {
        "name": "TEXT DEFAULT ''",
        "shares": "REAL DEFAULT 0",
        "avg_cost": "REAL DEFAULT 0",
        "current_price": "REAL DEFAULT 0",
        "target_weight": "REAL DEFAULT 0",
        "asset_type": "TEXT DEFAULT 'Stock'",
        "sector": "TEXT DEFAULT ''",
    }
    for col, spec in holding_defaults.items():
        if col not in holding_cols:
            conn.execute(f"ALTER TABLE holdings ADD COLUMN {col} {spec}")

    tx_cols = _columns(conn, "transactions")
    tx_defaults = {
        "fees": "REAL DEFAULT 0",
        "note": "TEXT DEFAULT ''",
    }
    for col, spec in tx_defaults.items():
        if col not in tx_cols:
            conn.execute(f"ALTER TABLE transactions ADD COLUMN {col} {spec}")


def _seed_if_empty(conn):
    count = conn.execute("SELECT COUNT(*) FROM holdings").fetchone()[0]
    if count == 0:
        conn.execute(
            """
            INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("QQQI", "NEOS Nasdaq-100 High Income ETF", 132, 52, 54.69, 35, "ETF", "Income ETF"),
        )
        conn.execute(
            """
            INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("CASH", "Cash", 10, 1, 1, 10, "Cash", "Cash"),
        )

    wcount = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
    if wcount == 0:
        rows = [
            ("TSM", "Taiwan Semiconductor ADR", 370, 390, 5, "AI infrastructure leader", 432.35),
            ("MSFT", "Microsoft", 420, 380, 4, "Quality compounder", 372.97),
            ("NVDA", "NVIDIA", 160, 170, 4, "AI leader, valuation sensitive", 192.53),
            ("AVGO", "Broadcom", 330, 340, 4, "AI networking and ASIC", 365.02),
        ]
        conn.executemany(
            """
            INSERT INTO watchlist (ticker, name, fair_value, target_buy_price, conviction, note, current_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
