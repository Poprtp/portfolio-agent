# AI Portfolio OS 4.6 — AI Trade Score

Replaces the manual pre-trade checklist with a rule-based Trade Assistant.

## Added
- Trade Score 0–100
- Recommendation: READY / REVIEW / WAIT
- Automatic reasons and risks
- Position sizing still uses entry, stop, target, cash, and risk %
- Trade Journal stores score and recommendation

## Notes
- This is a planning tool only.
- It does not place orders.
- It is rule-based, not connected to OpenAI yet.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
