from datetime import datetime

import pandas as pd

from services.database import connect, set_setting
from services.market import fetch_price, get_symbol_profile


def get_holdings() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query("SELECT * FROM holdings ORDER BY ticker", conn)


def get_enriched_holdings() -> pd.DataFrame:
    df = get_holdings()
    if df.empty:
        return df
    df = df[df["ticker"] != "CASH"].copy()
    for col in ["shares", "avg_cost", "current_price", "target_weight"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df = df[df["shares"] > 0].copy()
    if df.empty:
        return df
    df["market_value"] = df["shares"] * df["current_price"]
    df["cost_basis"] = df["shares"] * df["avg_cost"]
    df["gain_loss"] = df["market_value"] - df["cost_basis"]
    df["gain_loss_pct"] = df.apply(
        lambda r: (r["gain_loss"] / r["cost_basis"] * 100) if r["cost_basis"] else 0,
        axis=1,
    )
    total = df["market_value"].sum()
    df["weight"] = df["market_value"].apply(lambda v: v / total * 100 if total else 0)
    for col in ["shares", "avg_cost", "current_price", "market_value", "cost_basis", "gain_loss", "gain_loss_pct", "weight", "target_weight"]:
        df[col] = df[col].round(2)
    return df.sort_values("market_value", ascending=False)


def portfolio_summary() -> dict:
    df = get_enriched_holdings()
    if df.empty:
        return {
            "total_value": 0,
            "total_cost": 0,
            "total_gain_loss": 0,
            "total_return_pct": 0,
            "positions": 0,
            "risk_label": "Low",
            "risk_score": 0,
        }
    total = float(df["market_value"].sum())
    cost = float(df["cost_basis"].sum())
    gain = float(df["gain_loss"].sum())
    max_weight = float(df["weight"].max()) if not df.empty else 0
    positions = int(len(df))
    risk_score = min(100, round(20 + max(0, max_weight - 35) * 0.9 + (15 if positions <= 1 else 0)))
    risk_label = "High" if risk_score >= 75 else "Medium" if risk_score >= 45 else "Low"
    return {
        "total_value": round(total, 2),
        "total_cost": round(cost, 2),
        "total_gain_loss": round(gain, 2),
        "total_return_pct": round(gain / cost * 100, 2) if cost else 0,
        "positions": positions,
        "risk_label": risk_label,
        "risk_score": int(risk_score),
    }


def upsert_holding_auto(ticker: str, shares: float, avg_cost: float):
    ticker = str(ticker).upper().strip()
    shares = float(shares or 0)
    avg_cost = float(avg_cost or 0)
    profile = get_symbol_profile(ticker)
    current_price = profile.get("current_price") or avg_cost
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
            (
                ticker,
                profile.get("name") or ticker,
                shares,
                avg_cost,
                current_price,
                profile.get("target_weight", 10.0),
                profile.get("asset_type", "Stock"),
                profile.get("sector", ""),
            ),
        )
    return profile


def delete_holding(ticker: str):
    with connect() as conn:
        conn.execute("DELETE FROM holdings WHERE ticker=? AND ticker!='CASH'", (str(ticker).upper().strip(),))


def refresh_prices() -> dict:
    df = get_holdings()
    updated = 0
    fallback = 0
    with connect() as conn:
        for _, row in df.iterrows():
            ticker = row["ticker"]
            if ticker == "CASH":
                continue
            price, status = fetch_price(ticker, row.get("current_price", 0))
            conn.execute("UPDATE holdings SET current_price=? WHERE ticker=?", (price, ticker))
            if status == "updated":
                updated += 1
            else:
                fallback += 1
    set_setting("last_price_sync", datetime.now().strftime("%Y-%m-%d %H:%M"))
    return {"updated": updated, "fallback": fallback}


def top_risk_notes(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["No holdings yet"]
    notes = []
    top = df.iloc[0]
    if float(top["weight"]) > 50:
        notes.append(f"{top['ticker']} is concentrated at {top['weight']:.1f}%")
    losers = df[df["gain_loss_pct"] < -8]
    if not losers.empty:
        notes.append(f"Review losing position: {losers.iloc[0]['ticker']} {losers.iloc[0]['gain_loss_pct']:.1f}%")
    if not notes:
        notes.append("Portfolio risk is acceptable for now")
    return notes[:3]
