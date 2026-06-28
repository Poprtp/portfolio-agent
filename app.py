from datetime import date

import streamlit as st

from services.database import init_db, seed_default_data
from services.portfolio import (
    add_transaction,
    delete_holding,
    get_enriched_holdings,
    get_transactions,
    portfolio_summary,
    rebalance_actions,
    upsert_holding,
)
from services.watchlist import delete_watchlist, get_watchlist, upsert_watchlist
from utils.charts import allocation_chart
from utils.formatting import pct, usd

st.set_page_config(page_title="AI Portfolio OS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
init_db()
seed_default_data()

st.markdown(
    """
<style>
.block-container {padding: 1.1rem 1.6rem 1rem 1.6rem; max-width: 1180px;}
h1 {font-size: 1.55rem !important; margin-bottom: .05rem !important; letter-spacing: -0.02em;}
h2 {font-size: 1.1rem !important; margin-top: .65rem !important; margin-bottom: .35rem !important;}
h3 {font-size: 1rem !important; margin-top: .5rem !important;}
[data-testid="stSidebar"] {background: #111827;}
[data-testid="stSidebar"] .block-container {padding-top: 1.1rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #1f2937; border-radius:14px; padding:12px 14px;}
[data-testid="stMetricLabel"] {font-size:.72rem; color:#9ca3af;}
[data-testid="stMetricValue"] {font-size:1.28rem;}
.stDataFrame {border:1px solid #1f2937; border-radius:12px; overflow:hidden;}
.small-muted {color:#9ca3af; font-size:.78rem;}
.action-card {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:10px 12px; margin-bottom:8px;}
.action-card strong {font-size:.9rem;}
.green {color:#22c55e;} .red {color:#ef4444;} .muted {color:#9ca3af;}
hr {border-color:#1f2937; margin:.9rem 0;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- sidebar ----------
st.sidebar.markdown("### AI Portfolio")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Portfolio", "Transactions", "Watchlist", "Settings"],
    label_visibility="collapsed",
)
st.sidebar.divider()
if st.sidebar.button("Refresh data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption("MVP: portfolio, transactions, watchlist, dashboard.")

# ---------- shared data ----------
df = get_enriched_holdings()
summary = portfolio_summary()


def kpi_row():
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio", usd(summary["total_value"]))
    c2.metric("Gain / Loss", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    c3.metric("Cash", usd(summary["cash"]), pct(summary["cash_weight"]))
    c4.metric("Positions", str(summary["positions"]), f'Risk {summary["risk_score"]}/100')


def compact_holdings_table(height=270):
    cols = ["ticker", "shares", "avg_cost", "current_price", "market_value", "gain_loss_pct", "weight"]
    show = df[cols].copy() if not df.empty else df
    if not show.empty:
        show = show.rename(
            columns={
                "ticker": "Ticker",
                "shares": "Shares",
                "avg_cost": "Avg",
                "current_price": "Price",
                "market_value": "Value",
                "gain_loss_pct": "P/L %",
                "weight": "Weight %",
            }
        )
    st.dataframe(show, use_container_width=True, hide_index=True, height=height)


def action_cards():
    actions = rebalance_actions(df)
    if actions.empty:
        st.info("No actions yet.")
        return
    for _, row in actions.head(5).iterrows():
        ticker = row["ticker"]
        action = row["action"]
        drift = float(row["weight"] - row["target_weight"])
        badge = "HOLD"
        color = "muted"
        if "Add" in action:
            badge = "ADD"
            color = "green"
        elif "Stop" in action:
            badge = "STOP"
            color = "red"
        st.markdown(
            f"""
<div class="action-card">
  <strong>{ticker}</strong> <span class="{color}">{badge}</span><br>
  <span class="muted">{action} · drift {drift:.1f}%</span>
</div>
""",
            unsafe_allow_html=True,
        )


def recent_transaction_cards():
    tx = get_transactions(limit=5)
    if tx.empty:
        st.info("No transactions yet.")
        return
    for _, row in tx.iterrows():
        amount = float(row["shares"]) * float(row["price"])
        st.markdown(
            f"""
<div class="action-card">
  <strong>{row['action']} {row['ticker']}</strong><br>
  <span class="muted">{row['shares']:g} @ {usd(row['price'])} · {usd(amount)} · {row['date']}</span>
</div>
""",
            unsafe_allow_html=True,
        )


# ---------- pages ----------
if page == "Dashboard":
    st.title("Dashboard")
    st.caption("Compact portfolio overview")
    kpi_row()

    left, right = st.columns([1.35, 1], gap="medium")
    with left:
        st.subheader("Holdings")
        compact_holdings_table(265)
    with right:
        st.subheader("Allocation")
        st.plotly_chart(allocation_chart(df), use_container_width=True)

    b1, b2 = st.columns([1, 1], gap="medium")
    with b1:
        st.subheader("Actions")
        action_cards()
    with b2:
        st.subheader("Recent Transactions")
        recent_transaction_cards()

elif page == "Portfolio":
    st.title("Portfolio")
    st.caption("Edit current holdings")
    compact_holdings_table(320)

    st.subheader("Add / Edit Holding")
    with st.form("holding_form"):
        c1, c2, c3 = st.columns([1, 2, 1])
        ticker = c1.text_input("Ticker", value="TSM").upper().strip()
        name = c2.text_input("Name", value="Taiwan Semiconductor ADR")
        asset_type = c3.selectbox("Type", ["Stock", "ETF", "Cash", "Crypto", "Other"])
        c4, c5, c6 = st.columns(3)
        shares = c4.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
        avg_cost = c5.number_input("Average Cost", min_value=0.0, value=0.0, step=1.0)
        target_weight = c6.number_input("Target Weight %", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
        sector = st.text_input("Sector", value="Semiconductors")
        if st.form_submit_button("Save holding", use_container_width=True) and ticker:
            upsert_holding(ticker, name, shares, avg_cost, target_weight, asset_type, sector)
            st.success(f"Saved {ticker}")
            st.rerun()

    if not df.empty:
        st.subheader("Delete Holding")
        candidates = [t for t in df["ticker"].tolist() if t != "CASH"]
        if candidates:
            del_ticker = st.selectbox("Ticker", candidates)
            if st.button("Delete", type="secondary"):
                delete_holding(del_ticker)
                st.warning(f"Deleted {del_ticker}")
                st.rerun()

elif page == "Transactions":
    st.title("Transactions")
    st.caption("Record buys, sells, dividends, and cash movements")
    with st.form("tx_form"):
        c1, c2, c3 = st.columns(3)
        tx_date = c1.date_input("Date", value=date.today())
        ticker = c2.text_input("Ticker", value="TSM").upper().strip()
        action = c3.selectbox("Action", ["BUY", "SELL", "DIVIDEND", "CASH_IN", "CASH_OUT"])
        c4, c5, c6 = st.columns(3)
        shares = c4.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
        price = c5.number_input("Price / Cash Amount", min_value=0.0, value=0.0, step=1.0)
        fees = c6.number_input("Fees", min_value=0.0, value=0.0, step=0.1)
        note = st.text_input("Note", value="")
        if st.form_submit_button("Save transaction", use_container_width=True) and ticker:
            add_transaction(tx_date, ticker, action, shares, price, fees, note)
            st.success("Saved.")
            st.rerun()

    st.subheader("History")
    st.dataframe(get_transactions(), use_container_width=True, hide_index=True, height=360)

elif page == "Watchlist":
    st.title("Watchlist")
    st.caption("Simple ranking by conviction, fair value, and buy zone")
    wdf = get_watchlist()
    if not wdf.empty:
        keep = ["ticker", "name", "current_price", "fair_value", "target_buy_price", "conviction", "score"]
        st.dataframe(wdf[keep], use_container_width=True, hide_index=True, height=300)
    else:
        st.info("No watchlist yet.")

    st.subheader("Add / Edit")
    with st.form("watch_form"):
        c1, c2, c3 = st.columns(3)
        ticker = c1.text_input("Ticker", value="TSM").upper().strip()
        name = c2.text_input("Name", value="Taiwan Semiconductor ADR")
        conviction = c3.slider("Conviction", 1, 5, 4)
        c4, c5 = st.columns(2)
        fair_value = c4.number_input("Fair Value", min_value=0.0, value=370.0, step=1.0)
        target_buy = c5.number_input("Buy Zone", min_value=0.0, value=390.0, step=1.0)
        note = st.text_input("Note", value="")
        if st.form_submit_button("Save", use_container_width=True) and ticker:
            upsert_watchlist(ticker, name, fair_value, target_buy, conviction, note)
            st.success(f"Saved {ticker}")
            st.rerun()

    if not wdf.empty:
        del_ticker = st.selectbox("Delete ticker", wdf["ticker"].tolist())
        if st.button("Delete", type="secondary"):
            delete_watchlist(del_ticker)
            st.rerun()

elif page == "Settings":
    st.title("Settings")
    st.caption("Database and deployment")
    st.info("Storage on Streamlit Community Cloud may reset after redeploy. Keep important records backed up.")
    if st.button("Initialize / repair database"):
        init_db()
        seed_default_data()
        st.success("Database initialized.")
