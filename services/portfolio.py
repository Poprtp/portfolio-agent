from datetime import date

import pandas as pd

from services.database import connect
from services.market import fetch_price


def get_holdings() -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM holdings ORDER BY ticker", conn)
    return df


def get_enriched_holdings(include_cash: bool = True) -> pd.DataFrame:
    df = get_holdings()
    if df.empty:
        return df
    for col in ["shares", "avg_cost", "current_price", "target_weight"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["market_value"] = df["shares"] * df["current_price"]
    df["cost_basis"] = df["shares"] * df["avg_cost"]
    df["gain_loss"] = df["market_value"] - df["cost_basis"]
    df["gain_loss_pct"] = df.apply(
        lambda r: (r["gain_loss"] / r["cost_basis"] * 100) if r["cost_basis"] else 0, axis=1
    )
    total = df["market_value"].sum()
    df["weight"] = df["market_value"].apply(lambda v: v / total * 100 if total else 0)
    if not include_cash:
        df = df[df["ticker"] != "CASH"].copy()
    round_cols = ["shares", "avg_cost", "current_price", "market_value", "gain_loss", "gain_loss_pct", "weight", "target_weight"]
    for col in round_cols:
        if col in df.columns:
            df[col] = df[col].round(2)
    return df


def portfolio_summary() -> dict:
    df = get_enriched_holdings(include_cash=True)
    if df.empty:
        return {"total_value": 0, "total_gain_loss": 0, "total_return_pct": 0, "cash": 0, "cash_weight": 0, "positions": 0, "risk_score": 0}
    cash = float(df.loc[df["ticker"] == "CASH", "market_value"].sum())
    invest = df[df["ticker"] != "CASH"]
    total = float(df["market_value"].sum())
    gain = float(invest["gain_loss"].sum()) if not invest.empty else 0
    cost = float(invest["cost_basis"].sum()) if not invest.empty else 0
    cash_weight = cash / total * 100 if total else 0
    max_weight = float(invest["weight"].max()) if not invest.empty else 0
    risk = min(100, round(30 + max(0, max_weight - 35) * 0.9 + max(0, 10 - cash_weight) * 1.2))
    return {
        "total_value": round(total, 2),
        "total_gain_loss": round(gain, 2),
        "total_return_pct": round(gain / cost * 100, 2) if cost else 0,
        "cash": round(cash, 2),
        "cash_weight": round(cash_weight, 2),
        "positions": int(len(invest[invest["shares"] > 0])),
        "risk_score": int(risk),
    }


def upsert_holding(ticker, name, shares, avg_cost, target_weight, asset_type, sector, current_price=None):
    ticker = ticker.upper().strip()
    if not current_price:
        current_price = 1 if ticker == "CASH" else avg_cost
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name,
                shares=excluded.shares,
                avg_cost=excluded.avg_cost,
                current_price=excluded.current_price,
                target_weight=excluded.target_weight,
                asset_type=excluded.asset_type,
                sector=excluded.sector
            """,
            (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector),
        )


def delete_holding(ticker: str):
    with connect() as conn:
        conn.execute("DELETE FROM holdings WHERE ticker=? AND ticker!='CASH'", (ticker.upper().strip(),))


def get_transactions(limit: int | None = None) -> pd.DataFrame:
    q = "SELECT date, ticker, action, shares, price, fees, note FROM transactions ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with connect() as conn:
        return pd.read_sql_query(q, conn)


def _get_holding(conn, ticker):
    return conn.execute("SELECT ticker, shares, avg_cost, current_price FROM holdings WHERE ticker=?", (ticker,)).fetchone()


def _update_cash(conn, delta):
    row = _get_holding(conn, "CASH")
    if row is None:
        conn.execute("INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector) VALUES ('CASH','Cash',0,1,1,10,'Cash','Cash')")
    conn.execute("UPDATE holdings SET shares = COALESCE(shares,0) + ?, avg_cost=1, current_price=1 WHERE ticker='CASH'", (delta,))


def add_transaction(tx_date, ticker, action, shares, price, fees=0.0, note=""):
    ticker = ticker.upper().strip()
    action = action.upper().strip()
    shares = float(shares or 0)
    price = float(price or 0)
    fees = float(fees or 0)
    with connect() as conn:
        conn.execute(
            "INSERT INTO transactions (date, ticker, action, shares, price, fees, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(tx_date), ticker, action, shares, price, fees, note),
        )
        if action == "BUY" and ticker:
            cost = shares * price + fees
            row = _get_holding(conn, ticker)
            if row:
                old_shares = float(row[1] or 0)
                old_avg = float(row[2] or 0)
                new_shares = old_shares + shares
                new_avg = ((old_shares * old_avg) + cost) / new_shares if new_shares else 0
                conn.execute("UPDATE holdings SET shares=?, avg_cost=?, current_price=? WHERE ticker=?", (new_shares, new_avg, price, ticker))
            else:
                conn.execute(
                    "INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector) VALUES (?, ?, ?, ?, ?, 0, 'Stock', '')",
                    (ticker, ticker, shares, price, price),
                )
            _update_cash(conn, -cost)
        elif action == "SELL" and ticker:
            proceeds = shares * price - fees
            row = _get_holding(conn, ticker)
            if row:
                new_shares = max(0, float(row[1] or 0) - shares)
                conn.execute("UPDATE holdings SET shares=?, current_price=? WHERE ticker=?", (new_shares, price, ticker))
            _update_cash(conn, proceeds)
        elif action == "CASH_IN":
            _update_cash(conn, price)
        elif action == "CASH_OUT":
            _update_cash(conn, -price)


def refresh_prices() -> int:
    df = get_holdings()
    updated = 0
    with connect() as conn:
        for _, row in df.iterrows():
            ticker = row["ticker"]
            price = fetch_price(ticker, row.get("current_price", 0))
            conn.execute("UPDATE holdings SET current_price=? WHERE ticker=?", (price, ticker))
            updated += 1
    return updated


def rebalance_actions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ticker", "action"])
    rows = []
    for _, r in df.iterrows():
        ticker = r["ticker"]
        weight = float(r.get("weight", 0))
        target = float(r.get("target_weight", 0))
        if ticker == "CASH" and weight < target - 3:
            action = "Build cash"
        elif weight > target + 10 and target > 0:
            action = "Stop buying / trim later"
        elif weight < target - 5 and target > 0:
            action = "Add gradually"
        else:
            action = "Hold"
        rows.append({"ticker": ticker, "weight": weight, "target_weight": target, "action": action})
    return pd.DataFrame(rows)
