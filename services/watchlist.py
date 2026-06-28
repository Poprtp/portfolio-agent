import pandas as pd
from services.database import get_conn
from services.market import get_current_price


def upsert_watchlist(ticker, name, fair_value, target_buy_price, conviction, note=""):
    ticker = ticker.upper().strip()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO watchlist (ticker, name, fair_value, target_buy_price, conviction, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name, fair_value=excluded.fair_value, target_buy_price=excluded.target_buy_price,
                conviction=excluded.conviction, note=excluded.note, updated_at=CURRENT_TIMESTAMP
            """,
            (ticker, name, fair_value, target_buy_price, conviction, note),
        )
        conn.commit()


def delete_watchlist(ticker):
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker=?", (ticker.upper(),))
        conn.commit()


def get_watchlist() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY ticker", conn)
    if df.empty:
        return df
    df["current_price"] = df["ticker"].apply(get_current_price)
    discount = ((df["fair_value"] - df["current_price"]) / df["fair_value"].replace(0, pd.NA) * 100).fillna(0)
    buy_zone = (df["target_buy_price"] - df["current_price"]) / df["target_buy_price"].replace(0, pd.NA) * 100
    df["score"] = (df["conviction"] * 15 + discount.clip(-30, 30) + buy_zone.fillna(0).clip(-20, 20)).round(1)
    return df.sort_values("score", ascending=False)
