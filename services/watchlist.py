import pandas as pd

from services.database import connect
from services.market import fetch_price


def get_watchlist() -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY ticker", conn)
    if df.empty:
        return df
    for col in ["fair_value", "target_buy_price", "current_price", "conviction"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["score"] = df.apply(_score_row, axis=1).round(0).astype(int)
    df["mos_pct"] = df.apply(lambda r: ((r["fair_value"] - r["current_price"]) / r["fair_value"] * 100) if r["fair_value"] else 0, axis=1).round(1)
    return df.sort_values("score", ascending=False)


def _score_row(row) -> float:
    price = float(row.get("current_price", 0) or 0)
    fair = float(row.get("fair_value", 0) or 0)
    buy = float(row.get("target_buy_price", 0) or 0)
    conviction = int(row.get("conviction", 3) or 3)
    score = conviction * 12
    if price and fair:
        score += max(-20, min(30, (fair - price) / fair * 100))
    if price and buy and price <= buy:
        score += 20
    return max(0, min(100, score))


def upsert_watchlist(ticker, name, fair_value, target_buy_price, conviction, note):
    ticker = ticker.upper().strip()
    current = fetch_price(ticker, 0)
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
            (ticker, name, float(fair_value or 0), float(target_buy_price or 0), int(conviction or 3), note, current),
        )


def delete_watchlist(ticker):
    with connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker=?", (ticker.upper().strip(),))
