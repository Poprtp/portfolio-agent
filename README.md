# Portfolio OS V6.1 Sidebar + Nasdaq 50

Changes:
- Daily Desk stock cards are split into two columns.
- Watchlist management moved to the sidebar.
- Default baseline adds 50 Nasdaq-100 / QQQ-style large-cap tickers.
- Sidebar includes Refresh Data and Analyze Symbols controls.
- Existing holdings, journal, history, AI Advisor, and monotone design are preserved.

Deploy:
```powershell
git add .
git commit -m "Upgrade to Portfolio OS V6.1 sidebar Nasdaq watchlist"
git push
```

Then Streamlit Cloud: Clear cache -> Reboot app.
