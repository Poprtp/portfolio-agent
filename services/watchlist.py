from datetime import datetime

import pandas as pd

from services.database import connect, set_setting
from services.market import fetch_price


def _status(price: float, fair: float, buy: float) -> str:
    if price <= 0:
        return "NO PRICE"
    if buy > 0 and price <= buy:
        return "BUY ZONE"
    if fair > 0 and price <= fair:
        return "WATCH"
    return "EXPENSIVE"


def _mos(price: float, fair: float) -> float:
    if price <= 0 or fair <= 0:
        return 0.0
    return round((fair - price) / fair * 100, 1)


def _score_row(row) -> float:
    price = float(row.get("current_price", 0) or 0)
    fair = float(row.get("fair_value", 0) or 0)
    buy = float(row.get("target_buy_price", 0) or 0)
    conviction = int(row.get("conviction", 3) or 3)

    score = conviction * 10
    mos = _mos(price, fair)
    score += max(-25, min(35, mos))

    if price > 0 and buy > 0 and price <= buy:
        score += 25
    elif price > 0 and fair > 0 and price <= fair:
        score += 10

    return max(0, min(100, score))


def get_watchlist() -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY ticker", conn)
    if df.empty:
        return df
    for col in ["fair_value", "target_buy_price", "current_price", "conviction"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["mos"] = df.apply(lambda r: _mos(float(r["current_price"]), float(r["fair_value"])), axis=1)
    df["status"] = df.apply(lambda r: _status(float(r["current_price"]), float(r["fair_value"]), float(r["target_buy_price"])), axis=1)
    df["score"] = df.apply(_score_row, axis=1).round(0).astype(int)
    return df.sort_values(["score", "conviction"], ascending=False)


def get_top_opportunities(limit: int = 3) -> pd.DataFrame:
    df = get_watchlist()
    if df.empty:
        return df
    return df[df["status"].isin(["BUY ZONE", "WATCH"])].head(limit)


def upsert_watchlist(ticker, name, fair_value, target_buy_price, conviction, note):
    ticker = str(ticker).upper().strip()
    current, _ = fetch_price(ticker, 0)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO watchlist (ticker, name, fair_value, target_buy_price, conviction, note, current_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name,
                fair_value=excluded.fair_value,
                target_buy_price=excluded.target_buy_price,
                conviction=excluded.conviction,
                note=excluded.note,
                current_price=excluded.current_price
            """,
            (ticker, name, fair_value, target_buy_price, conviction, note, current),
        )


def delete_watchlist(ticker):
    with connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker=?", (str(ticker).upper().strip(),))


def refresh_watchlist_prices() -> dict:
    df = get_watchlist()
    updated = 0
    fallback = 0
    with connect() as conn:
        for _, row in df.iterrows():
            price, status = fetch_price(row["ticker"], row.get("current_price", 0))
            conn.execute("UPDATE watchlist SET current_price=? WHERE ticker=?", (price, row["ticker"]))
            if status == "updated":
                updated += 1
            elif status == "fallback":
                fallback += 1
    set_setting("last_watchlist_sync", datetime.now().strftime("%Y-%m-%d %H:%M"))
    return {"updated": updated, "fallback": fallback}
