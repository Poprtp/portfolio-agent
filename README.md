# Portfolio OS 5.4 — Homework UX

## Changes
- One-page desk stays the same: left Daily Desk, right Dashboard.
- Daily Desk stock rows are now collapsed by default.
- Each row shows only ticker, decision, and score until opened.
- Expanded view shows Buy Trigger, Stop, Target, R/R, setup explanation, and 30-minute homework checks.
- Added 30-Min Stock Homework logic:
  - Business clarity
  - Growth driver
  - Profit quality
  - Valuation risk
  - Exit plan
- Combined score now blends technical setup and homework quality.

## Deploy
```powershell
git add .
git commit -m "Upgrade to Portfolio OS 5.4 homework UX"
git push
```

Then Streamlit Cloud → Clear cache → Reboot app.
