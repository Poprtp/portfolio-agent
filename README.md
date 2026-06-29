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


## V6.2 Discord Alerts
- Added scheduled Discord alerts through GitHub Actions.
- Sends candidates when a symbol becomes READY or high-quality REVIEW / confirmation watch.
- Runs at 09:00 Bangkok daily.
- Runs at 09:00 New York on weekdays, about 30 minutes before the regular US market open.
- Added sidebar manual Discord test button.
- Scheduled alert symbols are stored in `config/alert_watchlist.txt`.

### Required setup
1. Create a Discord webhook in your Discord channel.
2. Add it to GitHub repository secrets as `DISCORD_WEBHOOK_URL`.
3. For the Streamlit manual test button, also add it to Streamlit Cloud secrets as `DISCORD_WEBHOOK_URL`.
4. Push the project. GitHub Actions will run from `.github/workflows/discord-alerts.yml`.

Note: GitHub Actions cannot read Streamlit Cloud's local SQLite database. Scheduled alerts use `config/alert_watchlist.txt`, while the live web app uses its own app watchlist.
