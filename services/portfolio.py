from datetime import date
import pandas as pd

from services.database import get_conn
from services.market import get_current_price


def get_holdings() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM holdings ORDER BY ticker", conn)


def upsert_holding(ticker, name, shares, avg_cost, target_weight, asset_type, sector):
    ticker = ticker.upper().strip()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO holdings (ticker, name, shares, avg_cost, target_weight, asset_type, sector, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name, shares=excluded.shares, avg_cost=excluded.avg_cost,
                target_weight=excluded.target_weight, asset_type=excluded.asset_type,
                sector=excluded.sector, updated_at=CURRENT_TIMESTAMP
            """,
            (ticker, name, shares, avg_cost, target_weight, asset_type, sector),
        )
        conn.commit()


def delete_holding(ticker):
    if ticker.upper() == "CASH":
        return
    with get_conn() as conn:
        conn.execute("DELETE FROM holdings WHERE ticker = ?", (ticker.upper(),))
        conn.commit()


def get_enriched_holdings() -> pd.DataFrame:
    df = get_holdings()
    if df.empty:
        return df
    df["current_price"] = df["ticker"].apply(get_current_price)
    df["market_value"] = df["shares"] * df["current_price"]
    invested = df["shares"] * df["avg_cost"]
    df["gain_loss"] = df["market_value"] - invested
    df["gain_loss_pct"] = (df["gain_loss"] / invested.replace(0, pd.NA) * 100).fillna(0)
    total = float(df["market_value"].sum())
    df["weight"] = (df["market_value"] / total * 100).fillna(0) if total else 0
    return df


def portfolio_summary() -> dict:
    df = get_enriched_holdings()
    if df.empty:
        return {"total_value": 0, "total_gain_loss": 0, "total_return_pct": 0, "cash": 0, "cash_weight": 0, "positions": 0, "risk_score": 0}
    total = float(df["market_value"].sum())
    invested = float((df["shares"] * df["avg_cost"]).sum())
    gain = total - invested
    cash = float(df.loc[df["ticker"] == "CASH", "market_value"].sum())
    qmax = float(df["weight"].max()) if not df.empty else 0
    risk = min(100, int(25 + max(0, qmax - 25)))
    return {
        "total_value": total,
        "total_gain_loss": gain,
        "total_return_pct": (gain / invested * 100) if invested else 0,
        "cash": cash,
        "cash_weight": (cash / total * 100) if total else 0,
        "positions": int((df[(df["ticker"] != "CASH") & (df["shares"] > 0)]).shape[0]),
        "risk_score": risk,
    }


def rebalance_actions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ticker", "weight", "target_weight", "action"])
    rows = []
    for _, row in df.iterrows():
        drift = float(row["weight"] - row["target_weight"])
        if drift > 10:
            action = "Stop buying / trim later"
        elif drift < -5:
            action = "Add gradually"
        else:
            action = "Hold"
        rows.append({"ticker": row["ticker"], "weight": row["weight"], "target_weight": row["target_weight"], "action": action})
    return pd.DataFrame(rows).sort_values("ticker")


def add_transaction(tx_date, ticker, action, shares, price, fees=0, note=""):
    ticker = ticker.upper().strip()
    action = action.upper().strip()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO transactions (date, ticker, action, shares, price, fees, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(tx_date), ticker, action, shares, price, fees, note),
        )
        if action == "BUY":
            h = conn.execute("SELECT shares, avg_cost, name, target_weight, asset_type, sector FROM holdings WHERE ticker=?", (ticker,)).fetchone()
            if h:
                old_shares, old_avg, name, target_weight, asset_type, sector = h
                new_shares = float(old_shares) + float(shares)
                new_avg = ((float(old_shares) * float(old_avg)) + (float(shares) * float(price)) + float(fees)) / new_shares if new_shares else 0
                conn.execute("UPDATE holdings SET shares=?, avg_cost=?, updated_at=CURRENT_TIMESTAMP WHERE ticker=?", (new_shares, new_avg, ticker))
            else:
                conn.execute("INSERT INTO holdings (ticker, name, shares, avg_cost, target_weight, asset_type, sector) VALUES (?, ?, ?, ?, ?, ?, ?)", (ticker, ticker, shares, price, 10, "Stock", ""))
        elif action == "SELL":
            conn.execute("UPDATE holdings SET shares = MAX(shares - ?, 0), updated_at=CURRENT_TIMESTAMP WHERE ticker=?", (shares, ticker))
        elif action == "CASH_IN":
            conn.execute("UPDATE holdings SET shares = shares + ?, updated_at=CURRENT_TIMESTAMP WHERE ticker='CASH'", (price,))
        elif action == "CASH_OUT":
            conn.execute("UPDATE holdings SET shares = MAX(shares - ?, 0), updated_at=CURRENT_TIMESTAMP WHERE ticker='CASH'", (price,))
        conn.commit()


def get_transactions(limit=None) -> pd.DataFrame:
    sql = "SELECT date, ticker, action, shares, price, fees, note FROM transactions ORDER BY date DESC, id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn)
