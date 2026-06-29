import pandas as pd

from services.database import connect
from services.market import get_symbol_profile
from services.trade import professional_trade_setup


def get_watchlist() -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM watchlist ORDER BY ticker", conn)
    if df.empty:
        return df
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
                current_price=excluded.current_price
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
                "Decision": setup["decision"],
                "Score": setup["score"],
                "Price": setup["current_price"],
                "Entry": setup["entry"],
                "Stop": setup["stop"],
                "Target": setup["target"],
                "R/R": setup["risk_reward"],
                "Setup": setup["setup_type"],
                "Trend": setup["trend"],
                "Reason": "; ".join(setup.get("reasons", [])[:2]) or "; ".join(setup.get("risks", [])[:2]),
            }
        )
    result = pd.DataFrame(rows).sort_values(["Score", "Decision"], ascending=[False, True])
    if limit:
        return result.head(limit)
    return result
