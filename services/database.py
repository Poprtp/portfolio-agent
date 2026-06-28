from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/portfolio.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            shares REAL NOT NULL DEFAULT 0,
            avg_cost REAL NOT NULL DEFAULT 0,
            target_weight REAL NOT NULL DEFAULT 0,
            asset_type TEXT NOT NULL DEFAULT 'Stock',
            sector TEXT NOT NULL DEFAULT 'Unknown'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('BUY','SELL','DIVIDEND','CASH_IN','CASH_OUT')),
            shares REAL NOT NULL DEFAULT 0,
            price REAL NOT NULL DEFAULT 0,
            fees REAL NOT NULL DEFAULT 0,
            note TEXT DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            fair_value REAL NOT NULL DEFAULT 0,
            target_buy_price REAL NOT NULL DEFAULT 0,
            conviction INTEGER NOT NULL DEFAULT 3,
            note TEXT DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def seed_default_data() -> None:
    conn = get_connection()
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) AS c FROM holdings").fetchone()["c"]
    if count == 0:
        holdings = [
            ("QQQI", "NEOS Nasdaq-100 High Income ETF", 132, 52, 35, "ETF", "Income"),
            ("TSM", "Taiwan Semiconductor ADR", 0, 0, 20, "Stock", "Semiconductors"),
            ("NVDA", "NVIDIA", 0, 0, 15, "Stock", "Semiconductors"),
            ("AVGO", "Broadcom", 0, 0, 10, "Stock", "Semiconductors"),
            ("MSFT", "Microsoft", 0, 0, 10, "Stock", "Software"),
            ("CASH", "Cash", 10, 1, 10, "Cash", "Cash"),
        ]
        cur.executemany(
            "INSERT INTO holdings(ticker,name,shares,avg_cost,target_weight,asset_type,sector) VALUES (?,?,?,?,?,?,?)",
            holdings,
        )
        cur.execute("INSERT INTO transactions(date,ticker,action,shares,price,fees,note) VALUES (?,?,?,?,?,?,?)",
                    (datetime.now().date().isoformat(), "QQQI", "BUY", 132, 52, 0, "Initial position"))
        watchlist = [
            ("TSM", "Taiwan Semiconductor ADR", 370, 390, 5, "Core AI infrastructure"),
            ("MSFT", "Microsoft", 420, 360, 5, "AI platform and cloud"),
            ("AVGO", "Broadcom", 390, 330, 4, "AI networking and ASIC"),
            ("NVDA", "NVIDIA", 185, 160, 4, "AI leader, valuation sensitive"),
            ("GOOGL", "Alphabet", 210, 180, 4, "AI and search platform"),
            ("AMZN", "Amazon", 240, 200, 4, "AWS and AI infrastructure"),
            ("META", "Meta Platforms", 760, 650, 4, "AI ads and infrastructure"),
        ]
        cur.executemany(
            "INSERT INTO watchlist(ticker,name,fair_value,target_buy_price,conviction,note) VALUES (?,?,?,?,?,?)",
            watchlist,
        )
    conn.commit()
    conn.close()
