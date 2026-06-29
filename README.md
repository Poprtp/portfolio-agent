# Portfolio OS V6.6 Large P/L Dashboard

Changes:
- Added AI Risk Engine for automatic position sizing.
- Daily Desk cards now show Suggested shares, Capital needed, Max loss, Position %, Stop distance, and Trigger distance.
- READY no longer means buy immediately; the trade also needs an acceptable AI Risk Plan.
- Save to Trade Journal now saves the AI risk plan and uses the selected risk-per-trade setting.
- Sidebar includes configurable professional defaults: Max risk per trade and Max position size.
- P/L Trend chart from V6.4 is preserved.

Deploy:
```powershell
git add .
git commit -m "Add AI risk sizing engine"
git push
```

Then Streamlit Cloud: Reboot app.


## V6.6 Large P/L Dashboard

- Moved P/L Trend to the top of the Dashboard column.
- Expanded P/L Trend to full right-column width.
- Increased chart height for easier reading.
- Moved Holdings below the chart.
- Kept Alerts and Risk Notes under Holdings.
