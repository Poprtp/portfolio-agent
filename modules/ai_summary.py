from __future__ import annotations

import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def generate_ai_summary(portfolio: pd.DataFrame, risk_notes: list[str]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "AI summary disabled. Add OPENAI_API_KEY to .env to enable it."

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        compact = portfolio[["ticker", "shares", "avg_cost", "current_price", "market_value", "weight", "target_weight", "gain_loss_pct", "drift"]].round(2).to_markdown(index=False)
        prompt = f"""
You are a conservative portfolio manager for a long-term investor.
Analyze this portfolio and give concise action items.
Avoid aggressive trading. Use DCA and risk control.

Portfolio:
{compact}

Risk notes:
{risk_notes}

Return sections:
1. Portfolio health
2. What to hold
3. What to add gradually
4. What to stop adding
5. This week's action plan
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content or "No AI summary returned."
    except Exception as e:
        return f"AI summary error: {e}"
