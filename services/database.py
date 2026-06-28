import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path('portfolio.db')
SEED_PATH = Path('data/seed_holdings.csv')


def connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = connect()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            shares REAL NOT NULL DEFAULT 0,
            avg_cost REAL NOT NULL DEFAULT 0,
            target_weight REAL NOT NULL DEFAULT 0
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            side TEXT NOT NULL,
            shares REAL NOT NULL,
            price REAL NOT NULL,
            notes TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            fair_value REAL NOT NULL DEFAULT 0,
            target_buy_price REAL NOT NULL DEFAULT 0,
            conviction INTEGER NOT NULL DEFAULT 50,
            notes TEXT
        )
    ''')
    count = cur.execute('SELECT COUNT(*) FROM holdings').fetchone()[0]
    if count == 0 and SEED_PATH.exists():
        seed = pd.read_csv(SEED_PATH)
        seed.to_sql('holdings', conn, if_exists='append', index=False)
    watch_count = cur.execute('SELECT COUNT(*) FROM watchlist').fetchone()[0]
    if watch_count == 0:
        rows = [
            ('TSM','Taiwan Semiconductor ADR',370,390,90,'Core AI infrastructure / foundry leader'),
            ('MSFT','Microsoft',420,360,88,'AI platform and cloud compounder'),
            ('AVGO','Broadcom',420,340,84,'AI networking and custom ASIC exposure'),
            ('NVDA','NVIDIA',190,165,80,'AI leader but valuation sensitive'),
            ('GOOGL','Alphabet',220,180,78,'AI + search + cloud optionality'),
        ]
        cur.executemany('INSERT OR IGNORE INTO watchlist VALUES (?,?,?,?,?,?)', rows)
    conn.commit()
    conn.close()


def read_table(table: str) -> pd.DataFrame:
    conn = connect()
    df = pd.read_sql_query(f'SELECT * FROM {table}', conn)
    conn.close()
    return df


def upsert_holding(ticker, name, shares, avg_cost, target_weight):
    conn = connect()
    conn.execute('''
        INSERT INTO holdings (ticker, name, shares, avg_cost, target_weight)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            name=excluded.name,
            shares=excluded.shares,
            avg_cost=excluded.avg_cost,
            target_weight=excluded.target_weight
    ''', (ticker.upper(), name, shares, avg_cost, target_weight))
    conn.commit()
    conn.close()


def delete_holding(ticker):
    conn = connect()
    conn.execute('DELETE FROM holdings WHERE ticker=?', (ticker.upper(),))
    conn.commit()
    conn.close()


def add_transaction(date, ticker, side, shares, price, notes=''):
    conn = connect()
    conn.execute('''
        INSERT INTO transactions (date, ticker, side, shares, price, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, ticker.upper(), side.upper(), shares, price, notes))
    conn.commit()
    conn.close()


def upsert_watchlist(ticker, name, fair_value, target_buy_price, conviction, notes):
    conn = connect()
    conn.execute('''
        INSERT INTO watchlist (ticker, name, fair_value, target_buy_price, conviction, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            name=excluded.name,
            fair_value=excluded.fair_value,
            target_buy_price=excluded.target_buy_price,
            conviction=excluded.conviction,
            notes=excluded.notes
    ''', (ticker.upper(), name, fair_value, target_buy_price, int(conviction), notes))
    conn.commit()
    conn.close()
