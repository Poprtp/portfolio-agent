from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime

from modules.portfolio import build_portfolio, load_holdings, save_holdings
from modules.risk import risk_score, action_label
from modules.rebalance import rebalance_suggestions
from modules.watchlist import score_watchlist
from modules.market_data import get_history
from modules.ai_summary import generate_ai_summary

st.set_page_config(page_title="AI Portfolio OS", page_icon="📊", layout="wide")

st.title("AI Portfolio OS 2.0")
st.caption("Portfolio dashboard, risk control, watchlist scoring, and AI review.")

with st.sidebar:
    st.header("Settings")
    new_cash = st.number_input("New cash to deploy (USD)", min_value=0.0, value=0.0, step=100.0)
    selected_period = st.selectbox("Chart period", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
    st.divider()
    st.write("Data file: `data/holdings.csv`")
    refresh = st.button("Refresh data")

portfolio = build_portfolio()
portfolio["action"] = portfolio.apply(action_label, axis=1)
portfolio_total = float(portfolio["market_value"].sum())
gain_loss = float(portfolio["gain_loss"].sum())
risk, notes = risk_score(portfolio)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio Value", f"${portfolio_total:,.2f}")
c2.metric("Total Gain/Loss", f"${gain_loss:,.2f}")
c3.metric("Risk Score", f"{risk}/100")
c4.metric("Positions", f"{len(portfolio[portfolio['ticker']!='CASH'])}")

st.subheader("Portfolio Allocation")
left, right = st.columns([1.2, 1])
with left:
    display_cols = ["ticker", "name", "shares", "avg_cost", "current_price", "market_value", "weight", "target_weight", "gain_loss_pct", "drift", "action"]
    st.dataframe(portfolio[display_cols].round(2), use_container_width=True, hide_index=True)
with right:
    fig = px.pie(portfolio, names="ticker", values="market_value", hole=0.45)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Risk Notes")
for note in notes:
    st.write(f"- {note}")

st.subheader("Rebalancing Plan")
rebalance = rebalance_suggestions(portfolio, new_cash=new_cash)
st.dataframe(rebalance[["ticker", "weight", "target_weight", "drift", "gap_to_target", "suggested_buy"]].round(2), use_container_width=True, hide_index=True)

st.subheader("Watchlist Ranking")
try:
    watchlist = score_watchlist()
    st.dataframe(watchlist[["ticker", "name", "current_price", "target_buy_zone", "pe", "profit_margin", "revenue_growth", "score", "notes"]].round(3), use_container_width=True, hide_index=True)
except Exception as e:
    st.warning(f"Could not load watchlist: {e}")

st.subheader("Price Chart")
chart_ticker = st.selectbox("Select ticker", [t for t in portfolio["ticker"].tolist() if t != "CASH"])
hist = get_history(chart_ticker, selected_period)
if not hist.empty:
    fig2 = px.line(hist, x="Date", y="Close", title=f"{chart_ticker} price history")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No chart data available.")

st.subheader("AI Portfolio Review")
if st.button("Generate AI Review"):
    with st.spinner("Generating AI review..."):
        st.markdown(generate_ai_summary(portfolio, notes))
else:
    st.info("Click Generate AI Review. Add OPENAI_API_KEY in .env to enable OpenAI summary.")

st.subheader("Edit Holdings")
with st.expander("Open holdings editor"):
    edited = st.data_editor(load_holdings(), num_rows="dynamic", use_container_width=True)
    if st.button("Save holdings"):
        save_holdings(edited)
        st.success("Saved. Click Refresh data or rerun the app.")

reports_dir = Path("reports")
reports_dir.mkdir(exist_ok=True)
if st.button("Export Current Report CSV"):
    out = reports_dir / f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    portfolio.to_csv(out, index=False)
    st.success(f"Saved: {out}")
