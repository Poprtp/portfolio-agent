# Portfolio OS V6.0.1 Hotfix

Fixes:
- Prevents Decision History SQLite conflict from crashing the app.
- Adds safer database migration for existing Streamlit Cloud databases.
- Removes the top header/caption text from the app.
- Keeps V6.0 features: AI Advisor, alerts, history, trade journal, one-page desk.

Update steps:
1. Copy all files into your local `D:\Portfolio-Agent` folder and overwrite existing files.
2. Run:

```powershell
git add .
git commit -m "Hotfix Portfolio OS V6.0.1"
git push
```

Then in Streamlit Cloud: Clear cache -> Reboot app.
