from __future__ import annotations

import pandas as pd
from services.database import get_connection
from services.market import get_price


def get_watchlist() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY conviction DESC, ticker", conn)
    conn.close()
    if df.empty:
        return df
    df["current_price"] = df["ticker"].apply(get_price)
    df["discount_to_fair_value_pct"] = ((df["fair_value"] - df["current_price"]) / df["current_price"].replace(0, pd.NA) * 100).fillna(0)
    df["distance_to_buy_zone_pct"] = ((df["current_price"] - df["target_buy_price"]) / df["target_buy_price"].replace(0, pd.NA) * 100).fillna(0)
    df["score"] = (df["conviction"] * 12 + df["discount_to_fair_value_pct"].clip(-30, 40) - df["distance_to_buy_zone_pct"].clip(-30, 50)).round(1)
    return df.sort_values("score", ascending=False)


def upsert_watchlist(ticker: str, name: str, fair_value: float, target_buy_price: float, conviction: int, note: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO watchlist(ticker,name,fair_value,target_buy_price,conviction,note)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(ticker) DO UPDATE SET
            name=excluded.name,
            fair_value=excluded.fair_value,
            target_buy_price=excluded.target_buy_price,
            conviction=excluded.conviction,
            note=excluded.note
        """,
        (ticker.upper(), name, fair_value, target_buy_price, conviction, note),
    )
    conn.commit()
    conn.close()


def delete_watchlist(ticker: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM watchlist WHERE ticker=?", (ticker.upper(),))
    conn.commit()
    conn.close()
