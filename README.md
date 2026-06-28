# AI Portfolio OS 4.0

MVP portfolio manager built with Streamlit, SQLite, yfinance, pandas, and Plotly.

## What changed in 4.0
- Portfolio page for holdings management.
- Transactions page for BUY / SELL / CASH_IN / CASH_OUT.
- Dashboard is read-only summary.
- Recent transactions are displayed from database.
- Risk label is Low / Medium / High instead of only numeric score.
- Watchlist remains simple.

## Run locally
```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Deploy
Push to GitHub, then reboot the Streamlit app.
