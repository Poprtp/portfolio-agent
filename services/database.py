from pathlib import Path
import sqlite3

DB_PATH = Path("data/portfolio.db")


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS holdings (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                shares REAL NOT NULL DEFAULT 0,
                avg_cost REAL NOT NULL DEFAULT 0,
                target_weight REAL NOT NULL DEFAULT 0,
                asset_type TEXT NOT NULL DEFAULT 'Stock',
                sector TEXT NOT NULL DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                shares REAL NOT NULL DEFAULT 0,
                price REAL NOT NULL DEFAULT 0,
                fees REAL NOT NULL DEFAULT 0,
                note TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                fair_value REAL NOT NULL DEFAULT 0,
                target_buy_price REAL NOT NULL DEFAULT 0,
                conviction INTEGER NOT NULL DEFAULT 3,
                note TEXT DEFAULT '',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def seed_default_data():
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM holdings").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT OR REPLACE INTO holdings (ticker, name, shares, avg_cost, target_weight, asset_type, sector) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    ("QQQI", "NEOS Nasdaq-100 High Income ETF", 132, 52, 35, "ETF", "Income"),
                    ("CASH", "Cash", 10, 1, 10, "Cash", "Cash"),
                ],
            )
            conn.execute(
                "INSERT INTO transactions (date, ticker, action, shares, price, fees, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("2026-06-28", "QQQI", "BUY", 132, 52, 0, "Initial position"),
            )
        wcount = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        if wcount == 0:
            conn.executemany(
                "INSERT OR REPLACE INTO watchlist (ticker, name, fair_value, target_buy_price, conviction, note) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    ("TSM", "Taiwan Semiconductor ADR", 370, 390, 5, "AI infrastructure"),
                    ("MSFT", "Microsoft", 420, 380, 4, "AI platform"),
                    ("AVGO", "Broadcom", 400, 350, 4, "AI networking"),
                ],
            )
        conn.commit()
