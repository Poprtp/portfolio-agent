from __future__ import annotations

from datetime import date
import pandas as pd
from services.database import get_connection
from services.market import enrich_prices


def get_holdings() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM holdings ORDER BY asset_type, ticker", conn)
    conn.close()
    return df


def get_enriched_holdings() -> pd.DataFrame:
    return enrich_prices(get_holdings())


def upsert_holding(ticker: str, name: str, shares: float, avg_cost: float, target_weight: float, asset_type: str, sector: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO holdings(ticker,name,shares,avg_cost,target_weight,asset_type,sector)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(ticker) DO UPDATE SET
            name=excluded.name,
            shares=excluded.shares,
            avg_cost=excluded.avg_cost,
            target_weight=excluded.target_weight,
            asset_type=excluded.asset_type,
            sector=excluded.sector
        """,
        (ticker.upper(), name, shares, avg_cost, target_weight, asset_type, sector),
    )
    conn.commit()
    conn.close()


def delete_holding(ticker: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM holdings WHERE ticker=?", (ticker.upper(),))
    conn.commit()
    conn.close()


def get_transactions() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC, id DESC", conn)
    conn.close()
    return df


def add_transaction(tx_date: date, ticker: str, action: str, shares: float, price: float, fees: float, note: str = "") -> None:
    ticker = ticker.upper()
    action = action.upper()
    conn = get_connection()
    conn.execute(
        "INSERT INTO transactions(date,ticker,action,shares,price,fees,note) VALUES(?,?,?,?,?,?,?)",
        (tx_date.isoformat(), ticker, action, shares, price, fees, note),
    )
    row = conn.execute("SELECT * FROM holdings WHERE ticker=?", (ticker,)).fetchone()
    if action == "BUY":
        if row:
            old_shares = float(row["shares"])
            old_cost = float(row["avg_cost"])
            new_shares = old_shares + shares
            new_avg = ((old_shares * old_cost) + (shares * price) + fees) / new_shares if new_shares else 0
            conn.execute("UPDATE holdings SET shares=?, avg_cost=? WHERE ticker=?", (new_shares, new_avg, ticker))
        else:
            conn.execute("INSERT INTO holdings(ticker,name,shares,avg_cost,target_weight,asset_type,sector) VALUES(?,?,?,?,?,?,?)",
                         (ticker, ticker, shares, price, 0, "Stock", "Unknown"))
    elif action == "SELL" and row:
        old_shares = float(row["shares"])
        new_shares = max(old_shares - shares, 0)
        conn.execute("UPDATE holdings SET shares=? WHERE ticker=?", (new_shares, ticker))
    elif action == "CASH_IN":
        conn.execute("INSERT INTO holdings(ticker,name,shares,avg_cost,target_weight,asset_type,sector) VALUES('CASH','Cash',0,1,10,'Cash','Cash') ON CONFLICT(ticker) DO NOTHING")
        conn.execute("UPDATE holdings SET shares=shares+? WHERE ticker='CASH'", (price,))
    elif action == "CASH_OUT":
        conn.execute("UPDATE holdings SET shares=max(shares-?,0) WHERE ticker='CASH'", (price,))
    conn.commit()
    conn.close()


def portfolio_summary() -> dict:
    df = get_enriched_holdings()
    total = float(df["market_value"].sum()) if not df.empty else 0.0
    gain = float(df["gain_loss"].sum()) if not df.empty else 0.0
    cash = float(df.loc[df["ticker"] == "CASH", "market_value"].sum()) if not df.empty else 0.0
    risk = calculate_risk_score(df)
    return {
        "total_value": total,
        "total_gain_loss": gain,
        "cash": cash,
        "cash_weight": (cash / total * 100) if total else 0,
        "risk_score": risk,
        "positions": int((df["shares"] > 0).sum()) if not df.empty else 0,
    }


def calculate_risk_score(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    score = 25
    max_weight = float(df["weight"].max()) if "weight" in df else 0
    if max_weight > 70:
        score += 40
    elif max_weight > 50:
        score += 30
    elif max_weight > 35:
        score += 20
    elif max_weight > 20:
        score += 10
    tech_weight = df.loc[df["sector"].isin(["Semiconductors", "Software"]), "weight"].sum()
    if tech_weight > 70:
        score += 20
    elif tech_weight > 50:
        score += 10
    cash_weight = df.loc[df["ticker"] == "CASH", "weight"].sum()
    if cash_weight < 5:
        score += 10
    return min(int(score), 100)


def rebalance_actions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df[["ticker", "name", "weight", "target_weight", "drift", "market_value"]].copy()
    def action(drift: float) -> str:
        if drift > 10:
            return "Trim / stop buying"
        if drift < -10:
            return "Buy / add gradually"
        return "Hold"
    out["action"] = out["drift"].apply(action)
    return out.sort_values("drift", ascending=False)
