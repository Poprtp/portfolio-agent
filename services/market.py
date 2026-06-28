import pandas as pd
import yfinance as yf

FALLBACK_PRICES = {
    'QQQI': 54.69,
    'TSM': 432.35,
    'NVDA': 192.53,
    'AVGO': 365.02,
    'MSFT': 372.97,
    'GOOGL': 185.00,
    'CASH': 1.00,
}


def get_price(ticker: str) -> float:
    ticker = ticker.upper()
    if ticker == 'CASH':
        return 1.0
    try:
        data = yf.Ticker(ticker).history(period='5d')
        if not data.empty:
            return float(data['Close'].dropna().iloc[-1])
    except Exception:
        pass
    return float(FALLBACK_PRICES.get(ticker, 0.0))


def get_prices(tickers):
    return {ticker: get_price(ticker) for ticker in tickers}


def get_history(ticker: str, period='1y') -> pd.DataFrame:
    if ticker.upper() == 'CASH':
        return pd.DataFrame()
    try:
        return yf.Ticker(ticker).history(period=period).reset_index()
    except Exception:
        return pd.DataFrame()
