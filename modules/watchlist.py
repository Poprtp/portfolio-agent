from __future__ import annotations

from pathlib import Path
import pandas as pd
from .market_data import get_latest_prices, get_basic_info

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
WATCHLIST_PATH = DATA_DIR / "watchlist.csv"


def load_watchlist() -> pd.DataFrame:
    df = pd.read_csv(WATCHLIST_PATH)
    df["ticker"] = df["ticker"].str.upper().str.strip()
    df["target_buy_zone"] = pd.to_numeric(df["target_buy_zone"], errors="coerce").fillna(0.0)
    return df


def score_watchlist() -> pd.DataFrame:
    df = load_watchlist()
    prices = get_latest_prices(df["ticker"].tolist())
    rows = []
    for _, row in df.iterrows():
        ticker = row["ticker"]
        price = prices.get(ticker, 0.0)
        info = get_basic_info(ticker)
        pe = info.get("trailingPE") or info.get("forwardPE") or 0
        margin = info.get("profitMargins") or 0
        revenue_growth = info.get("revenueGrowth") or 0
        score = 50
        if revenue_growth and revenue_growth > 0.1:
            score += 15
        if margin and margin > 0.2:
            score += 15
        if pe and pe < 35:
            score += 10
        elif pe and pe > 60:
            score -= 10
        buy_zone = float(row["target_buy_zone"])
        if buy_zone > 0 and price > 0:
            if price <= buy_zone:
                score += 15
            elif price <= buy_zone * 1.1:
                score += 5
            elif price > buy_zone * 1.2:
                score -= 10
        rows.append({**row.to_dict(), "current_price": price, "pe": pe, "profit_margin": margin, "revenue_growth": revenue_growth, "score": max(0, min(100, score))})
    return pd.DataFrame(rows).sort_values("score", ascending=False)
