# AI Portfolio OS 3.0

A clean Streamlit portfolio dashboard for holdings, transactions, watchlist, charts, risk scoring, and AI review.

## Local setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud

- Repository: your GitHub repo
- Branch: main
- Main file path: app.py
- Python runtime: python-3.11 from `runtime.txt`

## Optional OpenAI setup

In Streamlit Cloud → Manage app → Settings → Secrets:

```toml
OPENAI_API_KEY = "your_api_key_here"
```

## Files included

- `app.py` main landing page
- `pages/` Streamlit pages
- `services/` data, market, portfolio, and AI logic
- `data/seed_holdings.csv` initial holdings
- `.streamlit/config.toml` theme
- `requirements.txt`
- `runtime.txt`
