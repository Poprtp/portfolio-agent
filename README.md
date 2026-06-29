# Portfolio OS V6.0 — AI Advisor

One-page portfolio and trade desk with:
- Daily Desk with Buy Trigger / Stop / Target
- 30-minute stock homework logic
- Decision History snapshots
- Trade Journal planning
- Alert logic
- Optional GPT AI Advisor via `OPENAI_API_KEY`

## Deploy
Copy files over your existing repo, then:

```powershell
git add .
git commit -m "Upgrade to Portfolio OS V6.0 AI Advisor"
git push
```

Then Streamlit Cloud → Clear cache → Reboot app.

## Optional GPT Advisor
Add `OPENAI_API_KEY` in Streamlit Cloud secrets to enable GPT-generated advisor notes.
Without a key, the app uses the built-in rule-based advisor.
