from datetime import date

import streamlit as st

from services.database import init_db
from services.portfolio import (
    add_transaction,
    delete_holding,
    get_enriched_holdings,
    get_transactions,
    portfolio_summary,
    rebalance_actions,
    refresh_prices,
    upsert_holding,
)
from services.watchlist import delete_watchlist, get_watchlist, upsert_watchlist
from utils.charts import allocation_chart
from utils.formatting import pct, usd

st.set_page_config(page_title="AI Portfolio OS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
init_db()

st.markdown(
    """
<style>
.block-container {padding: .75rem 1.05rem 1rem 1.05rem; max-width: 1160px;}
h1 {font-size: 1.25rem !important; margin: 0 0 .35rem 0 !important; letter-spacing: -0.03em;}
h2 {font-size: 1.0rem !important; margin: .55rem 0 .25rem 0 !important;}
h3 {font-size: .9rem !important; margin: .45rem 0 .25rem 0 !important;}
[data-testid="stSidebar"] {background: #0f172a; border-right: 1px solid #1f2937; min-width: 215px !important; max-width: 215px !important;}
[data-testid="stSidebar"] .block-container {padding: 1rem .8rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:10px 12px;}
[data-testid="stMetricLabel"] {font-size:.72rem; color:#9ca3af;}
[data-testid="stMetricValue"] {font-size:1.05rem;}
.stDataFrame {border:1px solid #1f2937; border-radius:12px; overflow:hidden;}
.nav-row {display:flex; gap:.55rem; margin:.3rem 0 .7rem 0; align-items:center;}
.action-card {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:10px 12px; margin-bottom:8px;}
.action-card strong {font-size:.86rem;}
.green {color:#22c55e;} .red {color:#ef4444;} .muted {color:#9ca3af;} .blue {color:#60a5fa;}
hr {border-color:#1f2937; margin:.7rem 0;}
button[kind="secondary"] {border-radius:10px !important;}
</style>
""",
    unsafe_allow_html=True,
)

PAGES = ["Dashboard", "Portfolio", "Transactions", "Watchlist", "Settings"]
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
nav = st.session_state.page


def load_data():
    holdings = get_enriched_holdings(include_cash=False)
    all_holdings = get_enriched_holdings(include_cash=True)
    summary = portfolio_summary()
    return holdings, all_holdings, summary


holdings_df, all_df, summary = load_data()


def set_page(page):
    st.session_state.page = page
    st.rerun()


st.title("AI Portfolio OS")
nav_cols = st.columns([.85, .85, 1.05, .9, .85, 2.4])
for idx, page in enumerate(PAGES):
    active = page == nav
    with nav_cols[idx]:
        if st.button(page, use_container_width=True, type="primary" if active else "secondary"):
            set_page(page)


def kpi_row():
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio", usd(summary["total_value"]))
    c2.metric("Gain / Loss", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    c3.metric("Cash", usd(summary["cash"]), pct(summary["cash_weight"]))
    c4.metric("Positions", str(summary["positions"]), f'Risk {summary["risk_score"]}/100')


def holdings_table(df, height=220, full=False):
    if df.empty:
        st.info("No holdings yet.")
        return
    cols = ["ticker", "shares", "avg_cost", "current_price", "market_value", "gain_loss_pct", "weight"]
    if full:
        cols = ["ticker", "name", "shares", "avg_cost", "current_price", "market_value", "gain_loss", "gain_loss_pct", "weight", "target_weight", "sector"]
    show = df[cols].copy().rename(
        columns={
            "ticker": "Ticker",
            "name": "Name",
            "shares": "Shares",
            "avg_cost": "Avg",
            "current_price": "Price",
            "market_value": "Value",
            "gain_loss": "P/L",
            "gain_loss_pct": "P/L %",
            "weight": "Weight %",
            "target_weight": "Target %",
            "sector": "Sector",
        }
    )
    st.dataframe(show, use_container_width=True, hide_index=True, height=height)


def action_cards(limit=5):
    actions = rebalance_actions(all_df)
    if actions.empty:
        st.info("No actions yet.")
        return
    for _, row in actions.head(limit).iterrows():
        ticker = row["ticker"]
        action = row["action"]
        weight = float(row["weight"])
        target = float(row["target_weight"])
        badge, color = "HOLD", "muted"
        if "Add" in action or "Build" in action:
            badge, color = "ADD", "green"
        elif "Stop" in action:
            badge, color = "STOP", "red"
        st.markdown(
            f"""
<div class="action-card">
  <strong>{ticker}</strong> <span class="{color}">{badge}</span><br>
  <span class="muted">{action} · {weight:.1f}% vs target {target:.1f}%</span>
</div>
""",
            unsafe_allow_html=True,
        )


def recent_transaction_cards(limit=5):
    tx = get_transactions(limit=limit)
    if tx.empty:
        st.info("No transactions yet.")
        return
    for _, row in tx.iterrows():
        amount = float(row["shares"] or 0) * float(row["price"] or 0)
        if row["action"] in ["CASH_IN", "CASH_OUT", "DIVIDEND"]:
            amount = float(row["price"] or 0)
        st.markdown(
            f"""
<div class="action-card">
  <strong>{row['action']} {row['ticker']}</strong><br>
  <span class="muted">{row['shares']:g} @ {usd(row['price'])} · {usd(amount)} · {row['date']}</span>
</div>
""",
            unsafe_allow_html=True,
        )


with st.sidebar:
    st.markdown(f"### {nav}")
    st.caption("Quick actions")
    st.divider()

    if nav == "Dashboard":
        st.metric("Risk", f'{summary["risk_score"]}/100')
        st.caption("Top actions")
        action_cards(limit=3)

    elif nav == "Portfolio":
        st.caption("Add / Edit Holding")
        with st.form("holding_form"):
            ticker = st.text_input("Ticker", value="TSM").upper().strip()
            name = st.text_input("Name", value="Taiwan Semiconductor ADR")
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
            avg_cost = st.number_input("Average Cost", min_value=0.0, value=0.0, step=1.0)
            target_weight = st.number_input("Target %", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
            sector = st.text_input("Sector", value="Semiconductors")
            asset_type = st.selectbox("Type", ["Stock", "ETF", "Cash", "Crypto", "Other"])
            if st.form_submit_button("Save holding", use_container_width=True) and ticker:
                upsert_holding(ticker, name, shares, avg_cost, target_weight, asset_type, sector)
                st.rerun()
        if not holdings_df.empty:
            del_ticker = st.selectbox("Delete", holdings_df["ticker"].tolist())
            if st.button("Delete holding", use_container_width=True):
                delete_holding(del_ticker)
                st.rerun()

    elif nav == "Transactions":
        st.caption("Record Transaction")
        with st.form("tx_form"):
            tx_date = st.date_input("Date", value=date.today())
            ticker = st.text_input("Ticker", value="TSM").upper().strip()
            action = st.selectbox("Action", ["BUY", "SELL", "CASH_IN", "CASH_OUT", "DIVIDEND"])
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
            price = st.number_input("Price / Amount", min_value=0.0, value=0.0, step=1.0)
            fees = st.number_input("Fees", min_value=0.0, value=0.0, step=0.1)
            note = st.text_input("Note", value="")
            if st.form_submit_button("Save transaction", use_container_width=True) and ticker:
                add_transaction(tx_date, ticker, action, shares, price, fees, note)
                st.rerun()

    elif nav == "Watchlist":
        st.caption("Add / Edit Watchlist")
        with st.form("watch_form"):
            ticker = st.text_input("Ticker", value="TSM").upper().strip()
            name = st.text_input("Name", value="Taiwan Semiconductor ADR")
            conviction = st.slider("Conviction", 1, 5, 4)
            fair_value = st.number_input("Fair Value", min_value=0.0, value=370.0, step=1.0)
            target_buy = st.number_input("Buy Zone", min_value=0.0, value=390.0, step=1.0)
            note = st.text_input("Note", value="")
            if st.form_submit_button("Save watchlist", use_container_width=True) and ticker:
                upsert_watchlist(ticker, name, fair_value, target_buy, conviction, note)
                st.rerun()
        wdf = get_watchlist()
        if not wdf.empty:
            del_ticker = st.selectbox("Delete", wdf["ticker"].tolist())
            if st.button("Delete watchlist", use_container_width=True):
                delete_watchlist(del_ticker)
                st.rerun()

    elif nav == "Settings":
        if st.button("Repair database", use_container_width=True):
            init_db()
            st.success("Database ready")
        st.caption("Streamlit Cloud may reset SQLite after redeploy.")


if nav == "Dashboard":
    top_left, top_right = st.columns([1, .18])
    with top_left:
        st.caption("Compact portfolio dashboard")
    with top_right:
        if st.button("Refresh", use_container_width=True):
            refresh_prices()
            st.rerun()
    kpi_row()
    left, right = st.columns([1.25, 1], gap="medium")
    with left:
        st.subheader("Holdings")
        holdings_table(holdings_df, height=230)
    with right:
        st.subheader("Allocation")
        st.plotly_chart(allocation_chart(all_df), use_container_width=True)
    b1, b2 = st.columns([1, 1], gap="medium")
    with b1:
        st.subheader("Actions")
        action_cards()
    with b2:
        st.subheader("Recent Transactions")
        recent_transaction_cards()

elif nav == "Portfolio":
    st.caption("Manage current holdings")
    holdings_table(holdings_df, height=430, full=True)

elif nav == "Transactions":
    st.caption("Buy, sell, and cash movements")
    st.dataframe(get_transactions(), use_container_width=True, hide_index=True, height=470)

elif nav == "Watchlist":
    st.caption("Simple watchlist ranking")
    wdf = get_watchlist()
    if wdf.empty:
        st.info("No watchlist yet.")
    else:
        show = wdf[["ticker", "name", "current_price", "fair_value", "target_buy_price", "conviction", "score"]].rename(
            columns={
                "ticker": "Ticker",
                "name": "Name",
                "current_price": "Price",
                "fair_value": "Fair Value",
                "target_buy_price": "Buy Zone",
                "conviction": "Conviction",
                "score": "Score",
            }
        )
        st.dataframe(show, use_container_width=True, hide_index=True, height=430)

elif nav == "Settings":
    st.caption("Minimal settings")
    st.info("Use Repair database if old cloud database schema causes issues.")
