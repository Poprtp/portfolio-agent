from __future__ import annotations

import pandas as pd
from pathlib import Path
from .market_data import get_latest_prices

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
HOLDINGS_PATH = DATA_DIR / "holdings.csv"


def load_holdings() -> pd.DataFrame:
    df = pd.read_csv(HOLDINGS_PATH)
    df["ticker"] = df["ticker"].str.upper().str.strip()
    for col in ["shares", "avg_cost", "target_weight"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def save_holdings(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(HOLDINGS_PATH, index=False)


def build_portfolio() -> pd.DataFrame:
    df = load_holdings()
    prices = get_latest_prices(df["ticker"].tolist())
    df["current_price"] = df["ticker"].map(prices).fillna(0.0)
    df["market_value"] = df.apply(
        lambda r: r["shares"] * r["current_price"] if r["ticker"] != "CASH" else r["target_weight"],
        axis=1,
    )
    # For CASH row, target_weight is used as placeholder only in starter. User can edit market_value directly later.
    if "manual_value" in df.columns:
        df.loc[df["ticker"] == "CASH", "market_value"] = df.loc[df["ticker"] == "CASH", "manual_value"]
    total = float(df["market_value"].sum())
    df["weight"] = (df["market_value"] / total * 100) if total else 0
    df["cost_value"] = df["shares"] * df["avg_cost"]
    df.loc[df["ticker"] == "CASH", "cost_value"] = df.loc[df["ticker"] == "CASH", "market_value"]
    df["gain_loss"] = df["market_value"] - df["cost_value"]
    df["gain_loss_pct"] = (df["gain_loss"] / df["cost_value"].replace(0, pd.NA) * 100).fillna(0)
    df["drift"] = df["weight"] - df["target_weight"]
    return df
