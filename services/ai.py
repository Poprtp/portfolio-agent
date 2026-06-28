import os
from dotenv import load_dotenv

load_dotenv()


def generate_portfolio_review(metrics, top_positions, rebalance_df):
    api_key = os.getenv('OPENAI_API_KEY')
    base = f"""
Portfolio value: ${metrics.get('value',0):,.2f}
Total gain/loss: ${metrics.get('gain_loss',0):,.2f}
Risk score: {metrics.get('risk_score',0)}/100
Cash: ${metrics.get('cash',0):,.2f}

Top positions:
{top_positions.to_string(index=False) if top_positions is not None and not top_positions.empty else 'No positions'}

Rebalance actions:
{rebalance_df[['ticker','action','suggested_buy']].to_string(index=False) if rebalance_df is not None and not rebalance_df.empty else 'No actions'}
"""
    if not api_key:
        return (
            "### AI Review\n"
            "ยังไม่ได้ตั้งค่า OPENAI_API_KEY ดังนั้นระบบใช้ rule-based review ก่อน\n\n"
            + base +
            "\n**Action:** ถ้า QQQI เกิน 40% ให้หยุดซื้อเพิ่ม และใช้เงินใหม่ DCA เข้าหุ้น Growth/AI ที่ target weight ยังต่ำกว่าเป้า เช่น TSMC, MSFT, AVGO."
        )
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = "Analyze this portfolio in Thai. Give concise Buy/Hold/Trim and risk comments.\n" + base
        res = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role':'user','content':prompt}],
            temperature=0.2,
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"AI review failed: {e}\n\n{base}"
