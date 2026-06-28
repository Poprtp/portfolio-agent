from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import date

DB_PATH = os.path.join("data", "portfolio.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS holdings (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                shares REAL NOT NULL DEFAULT 0,
                avg_cost REAL NOT NULL DEFAULT 0,
                current_price REAL NOT NULL DEFAULT 0,
                target_weight REAL NOT NULL DEFAULT 0,
                asset_type TEXT NOT NULL DEFAULT 'Stock',
                sector TEXT NOT NULL DEFAULT ''
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
                note TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                current_price REAL NOT NULL DEFAULT 0,
                fair_value REAL NOT NULL DEFAULT 0,
                target_buy_price REAL NOT NULL DEFAULT 0,
                conviction INTEGER NOT NULL DEFAULT 3,
                note TEXT NOT NULL DEFAULT ''
            )
            """
        )
    ensure_schema()


def ensure_schema():
    """Add missing columns for older Streamlit Cloud databases."""
    with closing(get_conn()) as conn, conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(holdings)").fetchall()}
        required = {
            "current_price": "REAL NOT NULL DEFAULT 0",
            "target_weight": "REAL NOT NULL DEFAULT 0",
            "asset_type": "TEXT NOT NULL DEFAULT 'Stock'",
            "sector": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE holdings ADD COLUMN {column} {definition}")

        existing_w = {row[1] for row in conn.execute("PRAGMA table_info(watchlist)").fetchall()}
        required_w = {
            "current_price": "REAL NOT NULL DEFAULT 0",
            "fair_value": "REAL NOT NULL DEFAULT 0",
            "target_buy_price": "REAL NOT NULL DEFAULT 0",
            "conviction": "INTEGER NOT NULL DEFAULT 3",
            "note": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required_w.items():
            if column not in existing_w:
                conn.execute(f"ALTER TABLE watchlist ADD COLUMN {column} {definition}")

        conn.execute("UPDATE holdings SET current_price=avg_cost WHERE current_price IS NULL OR current_price=0")
        conn.execute("UPDATE holdings SET current_price=1, avg_cost=1 WHERE ticker='CASH'")


def seed_default_data():
    with closing(get_conn()) as conn, conn:
        cash_exists = conn.execute("SELECT 1 FROM holdings WHERE ticker='CASH'").fetchone()
        if not cash_exists:
            conn.execute(
                "INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("CASH", "Cash", 10, 1, 1, 10, "Cash", "Cash"),
            )
        q_exists = conn.execute("SELECT 1 FROM holdings WHERE ticker='QQQI'").fetchone()
        if not q_exists:
            conn.execute(
                "INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("QQQI", "NEOS Nasdaq-100 High Income ETF", 132, 52, 54.69, 35, "ETF", "Income ETF"),
            )
        for row in [
            ("TSM", "Taiwan Semiconductor ADR", 370, 390, 5, "Core AI hardware"),
            ("MSFT", "Microsoft", 430, 400, 4, "AI platform"),
            ("AVGO", "Broadcom", 380, 340, 4, "AI networking / ASIC"),
            ("NVDA", "NVIDIA", 190, 165, 3, "AI leader, valuation sensitive"),
        ]:
            exists = conn.execute("SELECT 1 FROM watchlist WHERE ticker=?", (row[0],)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO watchlist (ticker, name, fair_value, target_buy_price, conviction, note) VALUES (?, ?, ?, ?, ?, ?)",
                    row,
                )
