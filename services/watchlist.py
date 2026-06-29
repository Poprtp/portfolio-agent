import pandas as pd

from services.database import connect
from services.market import get_symbol_profile
from services.research import stock_homework
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


def _blend_decision(setup: dict, homework: dict) -> tuple[str, int]:
    tech_score = int(setup.get("score", 0) or 0)
    hw_score = int(homework.get("score", 50) or 50)
    score = int(max(0, min(100, round(tech_score * 0.68 + hw_score * 0.32))))

    red_flag = homework.get("valuation") == "High" or homework.get("profit_quality") == "Weak" or homework.get("business") == "Unclear"
    setup_type = str(setup.get("setup_type", "")).lower()
    no_clean = "no clean" in setup_type or "insufficient" in setup_type

    if score >= 78 and setup.get("decision") != "WAIT" and not red_flag and not no_clean:
        return "READY", score
    if score >= 58 and setup.get("decision") != "WAIT":
        return "REVIEW", score
    if score >= 64 and not red_flag and not no_clean:
        return "REVIEW", score
    return "WAIT", score


def trade_desk_watchlist(limit: int | None = None) -> pd.DataFrame:
    df = get_watchlist()
    if df.empty:
        return pd.DataFrame()
    rows = []
    for _, row in df.iterrows():
        ticker = row["ticker"]
        setup = professional_trade_setup(ticker)
        homework = stock_homework(ticker)
        decision, combined_score = _blend_decision(setup, homework)

        positive = setup.get("reasons", [])[:2]
        risks = setup.get("risks", [])[:2] + homework.get("risks", [])[:1]
        reason = "; ".join(positive) if positive else "; ".join(risks)
        if homework.get("summary"):
            reason = f"{reason}; {homework.get('summary')}" if reason else homework.get("summary")

        rows.append(
            {
                "Ticker": ticker,
                "Name": row.get("name", ticker),
                "Decision": decision,
                "Score": combined_score,
                "Technical Score": setup.get("score", 0),
                "Homework Score": homework.get("score", 0),
                "Price": setup.get("current_price", 0),
                "Entry": setup.get("entry", 0),
                "Stop": setup.get("stop", 0),
                "Target": setup.get("target", 0),
                "R/R": setup.get("risk_reward", 0),
                "Setup": setup.get("setup_type", ""),
                "Trend": setup.get("trend", ""),
                "Reason": reason,
                "Business": homework.get("business", "Unknown"),
                "Growth": homework.get("growth", "Unknown"),
                "Profit": homework.get("profit_quality", "Unknown"),
                "Valuation": homework.get("valuation", "Unknown"),
                "Exit": homework.get("exit_plan", "Stop/Thesis"),
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    order = {"READY": 0, "REVIEW": 1, "WAIT": 2}
    result["_rank"] = result["Decision"].map(order).fillna(9)
    result = result.sort_values(["_rank", "Score", "Ticker"], ascending=[True, False, True]).drop(columns=["_rank"])
    if limit:
        return result.head(limit)
    return result
