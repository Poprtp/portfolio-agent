import streamlit as st
from services.portfolio import get_enriched_holdings, portfolio_summary, rebalance_actions
from utils.formatting import usd, pct
from utils.charts import allocation_chart, bar_allocation

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("Dashboard")

df = get_enriched_holdings()
summary = portfolio_summary()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio Value", usd(summary["total_value"]))
c2.metric("Total Gain/Loss", usd(summary["total_gain_loss"]))
c3.metric("Cash", usd(summary["cash"]), pct(summary["cash_weight"]))
c4.metric("Risk Score", f'{summary["risk_score"]}/100')

st.divider()
left, right = st.columns([1.25, 1])
with left:
    st.subheader("Holdings")
    st.dataframe(df, use_container_width=True, hide_index=True)
with right:
    st.subheader("Allocation")
    st.plotly_chart(allocation_chart(df), use_container_width=True)

st.subheader("Allocation by Weight")
st.plotly_chart(bar_allocation(df), use_container_width=True)

st.subheader("Rebalance Actions")
st.dataframe(rebalance_actions(df), use_container_width=True, hide_index=True)
