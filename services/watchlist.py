from __future__ import annotations

from contextlib import closing

import pandas as pd

from services.database import get_conn
from services.market import get_latest_price


def upsert_watchlist(ticker, name, fair_value, target_buy_price, conviction, note=""):
    ticker = ticker.upper().strip()
    current_price = get_latest_price(ticker, 0)
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """
            INSERT INTO watchlist (ticker, name, current_price, fair_value, target_buy_price, conviction, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name,
                current_price=excluded.current_price,
                fair_value=excluded.fair_value,
                target_buy_price=excluded.target_buy_price,
                conviction=excluded.conviction,
                note=excluded.note
            """,
            (ticker, name, current_price, float(fair_value), float(target_buy_price), int(conviction), note),
        )


def delete_watchlist(ticker):
    with closing(get_conn()) as conn, conn:
        conn.execute("DELETE FROM watchlist WHERE ticker=?", (ticker.upper().strip(),))


def get_watchlist() -> pd.DataFrame:
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY ticker", conn)
    if df.empty:
        return df
    prices = []
    for _, row in df.iterrows():
        prices.append(get_latest_price(row["ticker"], row["current_price"]))
    df["current_price"] = prices
    df["upside_pct"] = df.apply(lambda r: 0 if r["current_price"] == 0 else ((r["fair_value"] - r["current_price"]) / r["current_price"]) * 100, axis=1)
    df["buy_zone_gap_pct"] = df.apply(lambda r: 0 if r["current_price"] == 0 else ((r["target_buy_price"] - r["current_price"]) / r["current_price"]) * 100, axis=1)
    df["score"] = (df["conviction"] * 12 + df["upside_pct"].clip(-20, 50) + df["buy_zone_gap_pct"].clip(-20, 20)).round(1)
    return df.sort_values("score", ascending=False)
