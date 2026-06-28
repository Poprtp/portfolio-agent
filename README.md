# AI Portfolio OS 3.8

Core stability update.

## What changed
- Cash is separated from active holdings on Dashboard.
- Positions no longer count Cash.
- BUY / SELL / CASH transactions update holdings and cash.
- Refresh button updates prices with yfinance and falls back safely.
- Cleaner rounded numbers and compact dashboard.

## Run locally
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Deploy
Push to GitHub, then reboot the Streamlit app.
