from __future__ import annotations

from datetime import date
from contextlib import closing

import pandas as pd

from services.database import get_conn
from services.market import get_latest_price


def get_holdings() -> pd.DataFrame:
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT * FROM holdings ORDER BY CASE WHEN ticker='CASH' THEN 1 ELSE 0 END, ticker", conn)
    return df


def upsert_holding(ticker, name, shares, avg_cost, target_weight, asset_type, sector, current_price=None):
    ticker = ticker.upper().strip()
    if current_price is None:
        current_price = 1.0 if ticker == "CASH" else avg_cost
    with closing(get_conn()) as conn, conn:
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
            (ticker, name, float(shares), float(avg_cost), float(current_price), float(target_weight), asset_type, sector),
        )


def delete_holding(ticker: str):
    ticker = ticker.upper().strip()
    if ticker == "CASH":
        return
    with closing(get_conn()) as conn, conn:
        conn.execute("DELETE FROM holdings WHERE ticker=?", (ticker,))


def refresh_prices():
    df = get_holdings()
    with closing(get_conn()) as conn, conn:
        for _, row in df.iterrows():
            ticker = row["ticker"]
            price = 1.0 if ticker == "CASH" else get_latest_price(ticker, row["current_price"])
            conn.execute("UPDATE holdings SET current_price=? WHERE ticker=?", (price, ticker))


def get_enriched_holdings() -> pd.DataFrame:
    df = get_holdings()
    if df.empty:
        return df
    df["market_value"] = df["shares"].astype(float) * df["current_price"].astype(float)
    df["cost_basis"] = df["shares"].astype(float) * df["avg_cost"].astype(float)
    df["gain_loss"] = df["market_value"] - df["cost_basis"]
    df["gain_loss_pct"] = df.apply(lambda r: 0 if r["cost_basis"] == 0 else (r["gain_loss"] / r["cost_basis"]) * 100, axis=1)
    total = float(df["market_value"].sum())
    df["weight"] = df["market_value"].apply(lambda v: 0 if total == 0 else (float(v) / total) * 100)
    numeric_cols = ["shares", "avg_cost", "current_price", "market_value", "cost_basis", "gain_loss", "gain_loss_pct", "weight", "target_weight"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(float).round(2)
    return df


def portfolio_summary() -> dict:
    df = get_enriched_holdings()
    if df.empty:
        return {"total_value": 0, "total_gain_loss": 0, "total_return_pct": 0, "cash": 0, "cash_weight": 0, "positions": 0, "risk_score": 0}
    cash_row = df[df["ticker"] == "CASH"]
    investment_df = df[df["ticker"] != "CASH"].copy()
    total_value = float(df["market_value"].sum())
    total_cost = float(investment_df["cost_basis"].sum())
    total_gain = float(investment_df["gain_loss"].sum())
    total_return_pct = 0 if total_cost == 0 else (total_gain / total_cost) * 100
    cash = float(cash_row["market_value"].sum()) if not cash_row.empty else 0.0
    cash_weight = 0 if total_value == 0 else cash / total_value * 100
    positions = int((investment_df["market_value"] > 0).sum())

    max_weight = float(investment_df["weight"].max()) if not investment_df.empty else 0
    concentration_risk = min(60, max_weight * 0.6)
    low_cash_risk = max(0, 10 - cash_weight) * 1.5
    few_positions_risk = max(0, 4 - positions) * 6
    risk_score = min(95, round(concentration_risk + low_cash_risk + few_positions_risk, 0))

    return {
        "total_value": round(total_value, 2),
        "total_gain_loss": round(total_gain, 2),
        "total_return_pct": round(total_return_pct, 1),
        "cash": round(cash, 2),
        "cash_weight": round(cash_weight, 1),
        "positions": positions,
        "risk_score": int(risk_score),
    }


def get_transactions(limit: int | None = None) -> pd.DataFrame:
    sql = "SELECT date, ticker, action, shares, price, fees, note FROM transactions ORDER BY id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    with closing(get_conn()) as conn:
        return pd.read_sql_query(sql, conn)


def _get_holding_row(conn, ticker: str):
    return conn.execute("SELECT * FROM holdings WHERE ticker=?", (ticker,)).fetchone()


def _cash_amount(conn) -> float:
    row = _get_holding_row(conn, "CASH")
    return float(row["shares"] if row else 0)


def _set_cash(conn, amount: float):
    upsert_sql = """
    INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector)
    VALUES ('CASH', 'Cash', ?, 1, 1, 10, 'Cash', 'Cash')
    ON CONFLICT(ticker) DO UPDATE SET shares=excluded.shares, current_price=1
    """
    conn.execute(upsert_sql, (round(float(amount), 2),))


def add_transaction(tx_date, ticker, action, shares, price, fees=0, note=""):
    ticker = ticker.upper().strip()
    action = action.upper().strip()
    shares = float(shares or 0)
    price = float(price or 0)
    fees = float(fees or 0)
    tx_date = str(tx_date or date.today())

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO transactions (date, ticker, action, shares, price, fees, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tx_date, ticker, action, shares, price, fees, note),
        )

        cash = _cash_amount(conn)
        if action == "CASH_IN":
            _set_cash(conn, cash + price)
            return
        if action == "CASH_OUT":
            _set_cash(conn, cash - price)
            return
        if action == "DIVIDEND":
            amount = price if shares == 0 else shares * price
            _set_cash(conn, cash + amount - fees)
            return

        if ticker == "CASH":
            return

        row = _get_holding_row(conn, ticker)
        old_shares = float(row["shares"]) if row else 0.0
        old_avg = float(row["avg_cost"]) if row else 0.0
        old_price = float(row["current_price"]) if row else price
        name = row["name"] if row else ticker
        target_weight = float(row["target_weight"]) if row else 0.0
        asset_type = row["asset_type"] if row else "Stock"
        sector = row["sector"] if row else ""

        if action == "BUY":
            new_shares = old_shares + shares
            new_avg = 0 if new_shares == 0 else ((old_shares * old_avg) + (shares * price) + fees) / new_shares
            _set_cash(conn, cash - (shares * price) - fees)
        elif action == "SELL":
            new_shares = max(0, old_shares - shares)
            new_avg = old_avg if new_shares > 0 else 0
            _set_cash(conn, cash + (shares * price) - fees)
        else:
            return

        conn.execute(
            """
            INSERT INTO holdings (ticker, name, shares, avg_cost, current_price, target_weight, asset_type, sector)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET shares=excluded.shares, avg_cost=excluded.avg_cost, current_price=excluded.current_price
            """,
            (ticker, name, round(new_shares, 4), round(new_avg, 4), old_price or price, target_weight, asset_type, sector),
        )


def rebalance_actions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ticker", "weight", "target_weight", "action"])
    rows = []
    for _, row in df.iterrows():
        ticker = row["ticker"]
        if float(row.get("market_value", 0)) <= 0:
            continue
        drift = float(row.get("weight", 0)) - float(row.get("target_weight", 0))
        if ticker == "CASH":
            action = "Build cash" if drift < -5 else "Hold cash"
        elif drift > 8:
            action = "Stop buying / trim later"
        elif drift < -5:
            action = "Add gradually"
        else:
            action = "Hold"
        rows.append({"ticker": ticker, "weight": round(row["weight"], 1), "target_weight": round(row["target_weight"], 1), "action": action})
    return pd.DataFrame(rows)
