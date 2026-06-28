import numpy as np
import pandas as pd
from services.market import get_prices


def enrich_holdings(holdings: pd.DataFrame) -> pd.DataFrame:
    if holdings.empty:
        return holdings
    df = holdings.copy()
    prices = get_prices(df['ticker'].tolist())
    df['current_price'] = df['ticker'].map(prices).astype(float)
    df['cost_basis'] = df['shares'] * df['avg_cost']
    df['market_value'] = df['shares'] * df['current_price']
    total = df['market_value'].sum()
    df['weight'] = np.where(total > 0, df['market_value'] / total * 100, 0)
    df['gain_loss'] = df['market_value'] - df['cost_basis']
    df['gain_loss_pct'] = np.where(df['cost_basis'] > 0, df['gain_loss'] / df['cost_basis'] * 100, 0)
    df['drift'] = df['weight'] - df['target_weight']
    return df.round(2)


def portfolio_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {'value': 0, 'gain_loss': 0, 'risk_score': 0, 'positions': 0, 'cash': 0}
    value = float(df['market_value'].sum())
    gain_loss = float(df['gain_loss'].sum()) if 'gain_loss' in df else 0
    max_weight = float(df['weight'].max()) if value else 0
    cash_weight = float(df.loc[df['ticker'].eq('CASH'), 'weight'].sum()) if 'ticker' in df else 0
    concentration_penalty = min(max_weight, 100) * 0.65
    cash_penalty = max(0, 10 - cash_weight) * 1.5
    risk_score = min(100, round(concentration_penalty + cash_penalty, 0))
    positions = int((df['market_value'] > 0).sum())
    cash = float(df.loc[df['ticker'].eq('CASH'), 'market_value'].sum()) if 'ticker' in df else 0
    return {'value': value, 'gain_loss': gain_loss, 'risk_score': risk_score, 'positions': positions, 'cash': cash}


def rebalance_actions(df: pd.DataFrame, new_cash: float = 0) -> pd.DataFrame:
    if df.empty:
        return df
    total_after_cash = df['market_value'].sum() + new_cash
    out = df[['ticker','name','market_value','weight','target_weight','drift']].copy()
    out['target_value'] = total_after_cash * out['target_weight'] / 100
    out['suggested_buy'] = (out['target_value'] - out['market_value']).clip(lower=0)
    out['action'] = out['drift'].apply(lambda x: 'Trim / stop adding' if x > 10 else ('Buy / DCA' if x < -5 else 'Hold'))
    return out.round(2)
