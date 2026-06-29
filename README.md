# Portfolio OS 5.3.1 Add Fix

Hotfix for one-page monotone Portfolio Desk.

Fixes:
- Watchlist Add now uses a form and shows feedback.
- Newly added tickers are not hidden by top-4 Skip Today limit anymore.
- Focus Today and Skip Today now show all watchlist items.
- Holdings Save now validates Ticker, Shares, and Avg Cost before saving.
- If Shares is 0, the app explains why it will not appear in Dashboard.

Deploy:

```powershell
git add .
git commit -m "Fix add watchlist and holdings visibility"
git push
```
