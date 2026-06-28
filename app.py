import streamlit as st
from services.database import init_db, seed_default_data
from services.portfolio import get_enriched_holdings, portfolio_summary, rebalance_actions, get_transactions
from utils.formatting import usd, pct
from utils.charts import allocation_chart

st.set_page_config(page_title="AI Portfolio OS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
init_db()
seed_default_data()

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 1rem; max-width: 1200px;}
h1 {font-size: 1.9rem !important; margin-bottom: 0.2rem !important;}
h2, h3 {margin-top: 0.6rem !important;}
[data-testid="stMetric"] {background:#111827; border:1px solid #1f2937; border-radius:14px; padding:14px 16px;}
[data-testid="stMetricLabel"] {font-size:0.78rem; color:#9ca3af;}
[data-testid="stMetricValue"] {font-size:1.45rem;}
.stDataFrame {border:1px solid #1f2937; border-radius:12px; overflow:hidden;}
.small-muted {color:#9ca3af; font-size:0.86rem;}
</style>
""", unsafe_allow_html=True)

st.title("AI Portfolio OS")
st.caption("Compact portfolio dashboard")

if st.sidebar.button("Refresh data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption("Use Portfolio to edit holdings and Transactions to record buys/sells.")

df = get_enriched_holdings()
summary = portfolio_summary()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio", usd(summary["total_value"]))
c2.metric("Gain / Loss", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
c3.metric("Cash", usd(summary["cash"]), pct(summary["cash_weight"]))
c4.metric("Risk", f'{summary["risk_score"]}/100', f'{summary["positions"]} positions')

left, right = st.columns([1.55, 1], gap="medium")
with left:
    st.subheader("Holdings")
    display_cols = ["ticker", "shares", "avg_cost", "current_price", "market_value", "gain_loss_pct", "weight", "target_weight"]
    show = df[display_cols].copy() if not df.empty else df
    if not show.empty:
        show = show.rename(columns={
            "ticker":"Ticker", "shares":"Shares", "avg_cost":"Avg", "current_price":"Price",
            "market_value":"Value", "gain_loss_pct":"P/L %", "weight":"Weight %", "target_weight":"Target %"
        })
    st.dataframe(show, use_container_width=True, hide_index=True, height=285)

with right:
    st.subheader("Allocation")
    st.plotly_chart(allocation_chart(df), use_container_width=True)

b1, b2 = st.columns([1, 1], gap="medium")
with b1:
    st.subheader("Actions")
    actions = rebalance_actions(df)
    if not actions.empty:
        st.dataframe(actions[["ticker", "weight", "target_weight", "action"]], use_container_width=True, hide_index=True, height=220)
    else:
        st.info("No actions yet.")
with b2:
    st.subheader("Recent Transactions")
    tx = get_transactions(limit=8)
    if tx.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(tx[["date", "ticker", "action", "shares", "price"]], use_container_width=True, hide_index=True, height=220)
