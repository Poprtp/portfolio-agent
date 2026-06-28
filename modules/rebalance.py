from __future__ import annotations

import pandas as pd


def rebalance_suggestions(portfolio: pd.DataFrame, new_cash: float = 0.0) -> pd.DataFrame:
    df = portfolio.copy()
    total = float(df["market_value"].sum()) + float(new_cash)
    df["target_value"] = total * df["target_weight"] / 100
    df["gap_to_target"] = df["target_value"] - df["market_value"]
    buys = df[df["gap_to_target"] > 0].copy()
    gap_sum = float(buys["gap_to_target"].sum())
    if gap_sum > 0 and new_cash > 0:
        buys["suggested_buy"] = buys["gap_to_target"] / gap_sum * new_cash
    else:
        buys["suggested_buy"] = 0.0
    df = df.merge(buys[["ticker", "suggested_buy"]], on="ticker", how="left")
    df["suggested_buy"] = df["suggested_buy"].fillna(0.0)
    return df
