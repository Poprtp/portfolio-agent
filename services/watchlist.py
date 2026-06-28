from datetime import datetime

import pandas as pd

from services.database import connect, set_setting
from services.market import fetch_price
from services.trade import professional_trade_setup


def _valuation_status(price: float, fair: float, buy: float) -> str:
    if price <= 0:
        return "NO PRICE"
    if buy > 0 and price <= buy:
        return "VALUE BUY ZONE"
    if fair > 0 and price <= fair:
        return "FAIR WATCH"
    return "VALUATION HIGH"


def _mos(price: float, fair: float) -> float:
    if price <= 0 or fair <= 0:
        return 0.0
    return round((fair - price) / fair * 100, 1)


def _valuation_score(price: float, fair: float, buy: float, conviction: int) -> int:
    mos = _mos(price, fair)
    score = conviction * 8
    score += max(-25, min(35, mos))
    if price > 0 and buy > 0 and price <= buy:
        score += 20
    elif price > 0 and fair > 0 and price <= fair:
        score += 10
    return int(max(0, min(100, score)))


def _decision(valuation_status: str, trade_action: str, technical_score: int) -> str:
    if trade_action == "READY" and valuation_status in ["VALUE BUY ZONE", "FAIR WATCH"]:
        return "ACTIONABLE"
    if trade_action == "READY" and valuation_status == "VALUATION HIGH":
        return "TECH READY / VALUATION HIGH"
    if trade_action == "REVIEW" and valuation_status in ["VALUE BUY ZONE", "FAIR WATCH"]:
        return "WATCH CLOSELY"
    if trade_action == "WAIT" and valuation_status in ["VALUE BUY ZONE", "FAIR WATCH"]:
        return "VALUE OK / WAIT SETUP"
    if technical_score >= 70:
        return "TECH WATCH"
    return "WAIT"


def get_watchlist() -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY ticker", conn)
    if df.empty:
        return df

    for col in ["fair_value", "target_buy_price", "current_price", "conviction"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    rows = []
    for _, row in df.iterrows():
        item = row.to_dict()
        price = float(item.get("current_price", 0) or 0)
        fair = float(item.get("fair_value", 0) or 0)
        buy = float(item.get("target_buy_price", 0) or 0)
        conviction = int(item.get("conviction", 3) or 3)

        setup = professional_trade_setup(item.get("ticker", ""))
        technical_score = int(setup.get("confidence", 0) or 0)
        trade_action = setup.get("recommendation", "WAIT")
        valuation_score = _valuation_score(price, fair, buy, conviction)
        valuation_status = _valuation_status(price, fair, buy)

        # Unified pro-trader score: technical setup first, valuation second, conviction last.
        total_score = int(max(0, min(100, round(technical_score * 0.55 + valuation_score * 0.30 + conviction * 4))))

        item.update(
            {
                "mos": _mos(price, fair),
                "valuation_status": valuation_status,
                "trade_action": trade_action,
                "technical_score": technical_score,
                "setup_type": setup.get("setup_type", ""),
                "decision": _decision(valuation_status, trade_action, technical_score),
                "score": total_score,
            }
        )
        rows.append(item)

    out = pd.DataFrame(rows)
    return out.sort_values(["score", "technical_score", "conviction"], ascending=False)


def get_top_opportunities(limit: int = 3) -> pd.DataFrame:
    df = get_watchlist()
    if df.empty:
        return df
    priority = df[df["decision"].isin(["ACTIONABLE", "WATCH CLOSELY", "TECH READY / VALUATION HIGH"])]
    if priority.empty:
        priority = df.head(limit)
    return priority.head(limit)


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
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY ticker", conn)
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
