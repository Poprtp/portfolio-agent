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


## V6.1.1 layout hotfix
- Added more top spacing so the top summary row is fully visible
- Fixed stock card overflow inside Daily Desk expanders
- Made trigger/homework blocks responsive to the column width


## V6.1.2 Plan Trade UX
- Renamed Plan trade to Save to Trade Journal.
- Shows a visible confirmation after saving a planned trade.
- Automatically opens Trade Journal after saving.
- Clarifies that saved plans do not execute orders.
- Disabled trade-plan saving for WAIT setups.


## V6.1.3 Delete Trade Journal
- Added Delete selected trade inside Trade Journal
- Added confirmation checkbox before deleting
- Trade Journal now shows more planned trades and includes trade IDs


## V6.1.4 Overnight price
- Added best-effort overnight / extended-hours quote fetching using yfinance.
- Sidebar has an Overnight Quote tool.
- Daily Desk cards can fetch overnight price per ticker.
- Quotes may be delayed or unavailable depending on Yahoo/yfinance coverage.


## V6.1.5 Top Safe Layout
- Increased safe top spacing so READY/REVIEW/WAIT and dashboard metric cards are fully visible.
- Added Streamlit header-safe CSS to prevent the top row from being clipped under the toolbar.
- Keeps all V6.1.4 overnight quote features.
