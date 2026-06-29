import sqlite3
from pathlib import Path

DB_PATH = Path("data/portfolio.db")
DB_PATH.parent.mkdir(exist_ok=True)


NASDAQ_TOP_50_WATCHLIST = [
    ('NVDA', 'NVIDIA', 5),
    ('AAPL', 'Apple', 5),
    ('MSFT', 'Microsoft', 5),
    ('AMZN', 'Amazon', 5),
    ('AVGO', 'Broadcom', 5),
    ('META', 'Meta Platforms', 5),
    ('GOOGL', 'Alphabet Class A', 5),
    ('GOOG', 'Alphabet Class C', 5),
    ('TSLA', 'Tesla', 4),
    ('NFLX', 'Netflix', 4),
    ('COST', 'Costco', 4),
    ('PLTR', 'Palantir', 4),
    ('ASML', 'ASML Holding', 4),
    ('AMD', 'Advanced Micro Devices', 4),
    ('CSCO', 'Cisco', 4),
    ('TMUS', 'T-Mobile US', 4),
    ('AZN', 'AstraZeneca', 4),
    ('LIN', 'Linde', 4),
    ('QCOM', 'Qualcomm', 4),
    ('INTU', 'Intuit', 4),
    ('AMAT', 'Applied Materials', 4),
    ('PEP', 'PepsiCo', 4),
    ('ISRG', 'Intuitive Surgical', 4),
    ('BKNG', 'Booking Holdings', 4),
    ('TXN', 'Texas Instruments', 4),
    ('AMGN', 'Amgen', 4),
    ('PANW', 'Palo Alto Networks', 4),
    ('ARM', 'Arm Holdings', 4),
    ('ADP', 'Automatic Data Processing', 4),
    ('GILD', 'Gilead Sciences', 4),
    ('CMCSA', 'Comcast', 3),
    ('MU', 'Micron Technology', 4),
    ('MELI', 'MercadoLibre', 4),
    ('HON', 'Honeywell', 3),
    ('LRCX', 'Lam Research', 4),
    ('APP', 'AppLovin', 4),
    ('CRWD', 'CrowdStrike', 4),
    ('KLAC', 'KLA Corporation', 4),
    ('ADI', 'Analog Devices', 3),
    ('SBUX', 'Starbucks', 3),
    ('MSTR', 'MicroStrategy', 3),
    ('CDNS', 'Cadence Design Systems', 4),
    ('SNPS', 'Synopsys', 4),
    ('ABNB', 'Airbnb', 3),
    ('MDLZ', 'Mondelez', 3),
    ('REGN', 'Regeneron', 3),
    ('MAR', 'Marriott', 3),
    ('ORLY', 'OReilly Automotive', 3),
    ('CTAS', 'Cintas', 3),
    ('FTNT', 'Fortinet', 3),
]


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
        _seed_nasdaq_top50(conn)


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



def _seed_nasdaq_top50(conn):
    """Keep a practical Nasdaq-100/QQQ-style top-50 baseline in the watchlist.
    Existing rows are preserved so user edits/removals do not get overwritten during the same session.
    """
    conn.executemany(
        """
        INSERT INTO watchlist (ticker, name, conviction)
        VALUES (?, ?, ?)
        ON CONFLICT(ticker) DO NOTHING
        """,
        NASDAQ_TOP_50_WATCHLIST,
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
