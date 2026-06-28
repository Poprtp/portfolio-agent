from datetime import date

import streamlit as st

from services.database import init_db
from services.market import price_history
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
from utils.charts import allocation_chart, price_chart
from utils.formatting import pct, usd

st.set_page_config(page_title="AI Portfolio OS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
init_db()

st.markdown(
    """
<style>
.block-container {padding: .55rem 1.05rem 1rem 1.05rem; max-width: 1180px;}
h1 {font-size: 1.1rem !important; margin: 0 0 .25rem 0 !important; letter-spacing: -0.03em;}
h2 {font-size: .98rem !important; margin: .75rem 0 .35rem 0 !important;}
h3 {font-size: .9rem !important; margin: .55rem 0 .25rem 0 !important;}
[data-testid="stSidebar"] {background: #0f172a; border-right: 1px solid #1f2937; min-width: 220px !important; max-width: 220px !important;}
[data-testid="stSidebar"] .block-container {padding: .9rem .8rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:10px 12px;}
[data-testid="stMetricLabel"] {font-size:.72rem; color:#9ca3af;}
[data-testid="stMetricValue"] {font-size:1.06rem;}
.stDataFrame {border:1px solid #1f2937; border-radius:11px; overflow:hidden;}
.nav-row {display:flex; gap:.65rem; align-items:center; margin:.45rem 0 .75rem 0;}
div.stButton > button {border-radius:10px; height:2.45rem; border:1px solid #253149; background:#111827; color:#e5e7eb; font-weight:650;}
div.stButton > button:hover {border-color:#60a5fa; color:white; background:#172033;}
.action-card {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:10px 12px; margin-bottom:8px;}
.action-card strong {font-size:.88rem;}
.green {color:#22c55e;} .red {color:#ef4444;} .muted {color:#9ca3af;} .blue {color:#60a5fa;} .orange {color:#f59e0b;}
.small-muted {color:#9ca3af; font-size:.78rem;}
hr {border-color:#1f2937; margin:.75rem 0;}
</style>
""",
    unsafe_allow_html=True,
)

PAGES = ["Dashboard", "Portfolio", "Transactions", "Watchlist", "Settings"]
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


def switch(page: str):
    st.session_state.page = page
    st.rerun()


def load_data():
    full_df = get_enriched_holdings(include_cash=True)
    invest_df = get_enriched_holdings(include_cash=False)
    summary_data = portfolio_summary()
    return full_df, invest_df, summary_data


full_df, invest_df, summary = load_data()
nav = st.session_state.page

# Header + top navigation
st.title("AI Portfolio OS")
nav_cols = st.columns([.75, .75, .95, .8, .75, 2.6])
for i, page in enumerate(PAGES):
    label = page
    button_type = "primary" if nav == page else "secondary"
    with nav_cols[i]:
        if st.button(label, type=button_type, use_container_width=True, key=f"nav_{page}"):
            switch(page)


def kpi_row():
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio", usd(summary["total_value"]))
    c2.metric("Gain / Loss", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    c3.metric("Cash", usd(summary["cash"]), pct(summary["cash_weight"]))
    c4.metric("Positions", str(summary["positions"]), summary["risk_label"])


def holdings_table(df, height=235, full=False):
    if df.empty:
        st.info("No holdings yet.")
        return
    cols = ["ticker", "shares", "avg_cost", "current_price", "market_value", "gain_loss_pct", "weight"]
    if full:
        cols = ["ticker", "name", "shares", "avg_cost", "current_price", "market_value", "gain_loss", "gain_loss_pct", "weight", "target_weight", "sector", "asset_type"]
    show = df[cols].copy()
    show = show.rename(columns={
        "ticker": "Ticker", "name": "Name", "shares": "Shares", "avg_cost": "Avg", "current_price": "Price",
        "market_value": "Value", "gain_loss": "P/L", "gain_loss_pct": "P/L %", "weight": "Weight %",
        "target_weight": "Target %", "sector": "Sector", "asset_type": "Type",
    })
    st.dataframe(show, use_container_width=True, hide_index=True, height=height)


def action_cards(limit=5):
    actions = rebalance_actions(full_df)
    if actions.empty:
        st.info("No actions yet.")
        return
    priority = actions.copy()
    priority["rank"] = priority["action"].map({"Stop buying": 0, "Build cash": 1, "Add gradually": 2, "Hold": 3}).fillna(9)
    for _, row in priority.sort_values("rank").head(limit).iterrows():
        ticker = row["ticker"]
        action = row["action"]
        target = float(row.get("target_weight", 0) or 0)
        weight = float(row.get("weight", 0) or 0)
        if action == "Stop buying":
            badge, color = "STOP", "red"
        elif action == "Build cash":
            badge, color = "ADD", "green"
        elif action == "Add gradually":
            badge, color = "ADD", "green"
        else:
            badge, color = "HOLD", "muted"
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
        action = row["action"]
        amount = float(row["price"] or 0) if action in ["CASH_IN", "CASH_OUT", "DIVIDEND"] else float(row["shares"] or 0) * float(row["price"] or 0)
        st.markdown(
            f"""
<div class="action-card">
  <strong>{action} {row['ticker']}</strong><br>
  <span class="muted">{row['shares']:g} @ {usd(row['price'])} · {usd(amount)} · {row['date']}</span>
</div>
""",
            unsafe_allow_html=True,
        )


# Contextual sidebar
with st.sidebar:
    st.markdown(f"### {nav}")
    st.caption("Quick actions")
    st.divider()

    if nav == "Dashboard":
        st.metric("Risk", summary["risk_label"], f'{summary["risk_score"]}/100')
        st.caption(summary["risk_note"])
        st.caption("Top actions")
        action_cards(limit=3)

    elif nav == "Portfolio":
        st.caption("Add / Edit Holding")
        with st.form("holding_form"):
            ticker = st.text_input("Ticker", value="TSM").upper().strip()
            name = st.text_input("Name", value="Taiwan Semiconductor ADR")
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
            avg_cost = st.number_input("Average Cost", min_value=0.0, value=0.0, step=1.0)
            current_price = st.number_input("Current Price", min_value=0.0, value=0.0, step=1.0)
            target_weight = st.number_input("Target %", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
            sector = st.text_input("Sector", value="Semiconductors")
            asset_type = st.selectbox("Type", ["Stock", "ETF", "Cash", "Crypto", "Other"])
            if st.form_submit_button("Save holding", use_container_width=True) and ticker:
                upsert_holding(ticker, name, shares, avg_cost, target_weight, asset_type, sector, current_price)
                st.success(f"Saved {ticker}")
                st.rerun()
        candidates = invest_df["ticker"].tolist() if not invest_df.empty else []
        if candidates:
            st.divider()
            del_ticker = st.selectbox("Delete", candidates)
            if st.button("Delete holding", use_container_width=True):
                delete_holding(del_ticker)
                st.rerun()

    elif nav == "Transactions":
        st.caption("Add Transaction")
        with st.form("tx_form"):
            tx_date = st.date_input("Date", value=date.today())
            action = st.selectbox("Action", ["BUY", "SELL", "CASH_IN", "CASH_OUT"])
            default_ticker = "CASH" if action in ["CASH_IN", "CASH_OUT"] else "TSM"
            ticker = st.text_input("Ticker", value=default_ticker).upper().strip()
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0, disabled=action in ["CASH_IN", "CASH_OUT"])
            price_label = "Amount" if action in ["CASH_IN", "CASH_OUT"] else "Price"
            price = st.number_input(price_label, min_value=0.0, value=0.0, step=1.0)
            fees = st.number_input("Fees", min_value=0.0, value=0.0, step=0.1)
            note = st.text_input("Note", value="")
            if st.form_submit_button("Save transaction", use_container_width=True):
                add_transaction(tx_date, ticker, action, shares, price, fees, note)
                st.success("Transaction saved")
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
                st.success(f"Saved {ticker}")
                st.rerun()
        wdf = get_watchlist()
        if not wdf.empty:
            st.divider()
            del_ticker = st.selectbox("Delete", wdf["ticker"].tolist())
            if st.button("Delete watchlist", use_container_width=True):
                delete_watchlist(del_ticker)
                st.rerun()

    elif nav == "Settings":
        if st.button("Initialize / repair database", use_container_width=True):
            init_db()
            st.success("Database checked")
            st.rerun()
        st.info("Streamlit Cloud storage can reset after redeploy. Keep important records backed up.")


# Pages
if nav == "Dashboard":
    top_l, top_r = st.columns([1, .18])
    with top_l:
        st.caption("Compact portfolio dashboard")
    with top_r:
        if st.button("Refresh", use_container_width=True):
            refresh_prices()
            st.cache_data.clear()
            st.rerun()
    kpi_row()
    left, right = st.columns([1.35, 1], gap="medium")
    with left:
        st.subheader("Holdings")
        holdings_table(invest_df, height=245)
    with right:
        st.subheader("Allocation")
        st.plotly_chart(allocation_chart(full_df), use_container_width=True)
    b1, b2 = st.columns([1, 1], gap="medium")
    with b1:
        st.subheader("Actions")
        action_cards()
    with b2:
        st.subheader("Recent Transactions")
        recent_transaction_cards()

elif nav == "Portfolio":
    st.caption("Manage current holdings")
    st.subheader("Current Holdings")
    holdings_table(invest_df, height=390, full=True)
    st.subheader("Cash")
    cash_df = full_df[full_df["ticker"] == "CASH"]
    holdings_table(cash_df, height=100, full=True)

elif nav == "Transactions":
    st.caption("Record buy, sell, and cash movements")
    st.subheader("Transactions")
    tx = get_transactions()
    if tx.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(tx, use_container_width=True, hide_index=True, height=470)

elif nav == "Watchlist":
    st.caption("Track possible buys")
    st.subheader("Watchlist")
    wdf = get_watchlist()
    if wdf.empty:
        st.info("No watchlist yet.")
    else:
        keep = ["ticker", "name", "current_price", "fair_value", "target_buy_price", "mos_pct", "conviction", "score"]
        show = wdf[keep].rename(columns={
            "ticker": "Ticker", "name": "Name", "current_price": "Price", "fair_value": "Fair Value",
            "target_buy_price": "Buy Zone", "mos_pct": "MOS %", "conviction": "Conviction", "score": "Score",
        })
        st.dataframe(show, use_container_width=True, hide_index=True, height=430)

elif nav == "Settings":
    st.caption("Maintenance")
    st.subheader("Settings")
    st.write("Use the sidebar to repair the database if schema errors appear after deploy.")
    st.code("streamlit run app.py")
