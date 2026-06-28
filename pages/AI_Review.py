import streamlit as st
from services.portfolio import get_enriched_holdings, portfolio_summary, rebalance_actions

st.set_page_config(page_title="AI Review", layout="wide")
st.title("AI Review")
st.caption("Rule-based review now. OpenAI-powered review will be added in the next sprint.")

df = get_enriched_holdings()
summary = portfolio_summary()
actions = rebalance_actions(df)

st.subheader("Portfolio Health")
risk = summary["risk_score"]
if risk >= 70:
    st.error(f"Risk score is high: {risk}/100")
elif risk >= 45:
    st.warning(f"Risk score is moderate: {risk}/100")
else:
    st.success(f"Risk score is healthy: {risk}/100")

st.subheader("Action Plan")
for _, row in actions.iterrows():
    if row["action"] != "Hold":
        st.write(f"- **{row['ticker']}**: {row['action']} because current weight is {row['weight']:.1f}% vs target {row['target_weight']:.1f}%.")

if actions[actions["action"] != "Hold"].empty:
    st.info("No major rebalance action required.")

st.subheader("Details")
st.dataframe(actions, use_container_width=True, hide_index=True)
