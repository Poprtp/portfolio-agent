import pandas as pd

from services.database import connect
from services.market import get_symbol_profile
from services.trade import professional_trade_setup


def get_watchlist() -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY ticker", conn)
    return df


def add_watchlist(ticker: str):
    ticker = str(ticker).upper().strip()
    if not ticker:
        return {}
    profile = get_symbol_profile(ticker)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO watchlist (ticker, name, conviction, current_price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name,
                current_price=excluded.current_price,
                conviction=COALESCE(watchlist.conviction, excluded.conviction)
            """,
            (ticker, profile.get("name") or ticker, 3, profile.get("current_price") or 0),
        )
    return profile


def delete_watchlist(ticker: str):
    with connect() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker=?", (str(ticker).upper().strip(),))


def trade_desk_watchlist(limit: int | None = None) -> pd.DataFrame:
    df = get_watchlist()
    if df.empty:
        return pd.DataFrame()
    rows = []
    for _, row in df.iterrows():
        ticker = row["ticker"]
        setup = professional_trade_setup(ticker)
        rows.append(
            {
                "Ticker": ticker,
                "Name": row.get("name", ticker),
                "Decision": setup.get("decision", "WAIT"),
                "Score": setup.get("score", 0),
                "Price": setup.get("current_price", row.get("current_price", 0) or 0),
                "Entry": setup.get("entry", 0),
                "Stop": setup.get("stop", 0),
                "Target": setup.get("target", 0),
                "R/R": setup.get("risk_reward", 0),
                "Setup": setup.get("setup_type", "No clean setup"),
                "Trend": setup.get("trend", "Unknown"),
                "Reason": "; ".join(setup.get("reasons", [])[:2]) or "; ".join(setup.get("risks", [])[:2]) or "Added to watchlist",
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    order = {"READY": 0, "REVIEW": 1, "WAIT": 2}
    result["_order"] = result["Decision"].map(order).fillna(3)
    result = result.sort_values(["_order", "Score", "Ticker"], ascending=[True, False, True]).drop(columns=["_order"])
    if limit:
        return result.head(limit)
    return result
