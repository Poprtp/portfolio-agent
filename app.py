from datetime import date

import streamlit as st

from services.database import init_db, seed_default_data
from services.market import get_price_history
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
from utils.charts import allocation_chart, price_chart
from utils.formatting import pct, usd

st.set_page_config(page_title="AI Portfolio OS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
init_db()
seed_default_data()

st.markdown(
    """
<style>
.block-container {padding: .85rem 1.15rem 1rem 1.15rem; max-width: 1180px;}
h1 {font-size: 1.35rem !important; margin: .05rem 0 .25rem 0 !important; letter-spacing: -0.03em;}
h2 {font-size: 1.0rem !important; margin: .7rem 0 .35rem 0 !important;}
h3 {font-size: .95rem !important; margin: .55rem 0 .25rem 0 !important;}
[data-testid="stSidebar"] {background: #0f172a; border-right: 1px solid #1f2937; min-width: 220px !important; max-width: 240px !important;}
[data-testid="stSidebar"] .block-container {padding-top: 1.05rem; padding-left: 1rem; padding-right: 1rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #1f2937; border-radius:13px; padding:10px 12px;}
[data-testid="stMetricLabel"] {font-size:.70rem; color:#9ca3af;}
[data-testid="stMetricValue"] {font-size:1.08rem;}
.stDataFrame {border:1px solid #1f2937; border-radius:11px; overflow:hidden;}
.small-muted {color:#9ca3af; font-size:.78rem;}
.action-card {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:10px 12px; margin-bottom:8px;}
.action-card strong {font-size:.86rem;}
.green {color:#22c55e;} .red {color:#ef4444;} .muted {color:#9ca3af;} .blue {color:#60a5fa;}
hr {border-color:#1f2937; margin:.8rem 0;}
/* Button navigation */
div[data-testid="stHorizontalBlock"] button {border-radius: 10px !important; font-weight: 650 !important;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- data ----------
df = get_enriched_holdings()
summary = portfolio_summary()

# ---------- navigation ----------
PAGES = ["Dashboard", "Portfolio", "Transactions", "Watchlist", "Settings"]
if "nav" not in st.session_state:
    st.session_state.nav = "Dashboard"
if st.session_state.nav not in PAGES:
    st.session_state.nav = "Dashboard"

st.title("AI Portfolio OS")
nav_cols = st.columns([.9, .9, 1.15, .95, .9, 4.1], gap="small")
for i, page in enumerate(PAGES):
    button_type = "primary" if st.session_state.nav == page else "secondary"
    if nav_cols[i].button(page, type=button_type, use_container_width=True):
        st.session_state.nav = page
        st.rerun()
nav = st.session_state.nav
st.caption("Compact portfolio dashboard")


# ---------- helpers ----------
def kpi_row():
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio", usd(summary["total_value"]))
    c2.metric("Gain / Loss", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    c3.metric("Cash", usd(summary["cash"]), pct(summary["cash_weight"]))
    c4.metric("Positions", str(summary["positions"]), f'Risk {summary["risk_score"]}/100')


def compact_holdings_table(height=245, full=False):
    if df.empty:
        st.info("No holdings yet.")
        return
    cols = ["ticker", "shares", "avg_cost", "current_price", "market_value", "gain_loss_pct", "weight"]
    if full:
        cols = ["ticker", "name", "shares", "avg_cost", "current_price", "market_value", "gain_loss_pct", "weight", "target_weight", "sector"]
    show = df[cols].copy()
    show = show.rename(
        columns={
            "ticker": "Ticker",
            "name": "Name",
            "shares": "Shares",
            "avg_cost": "Avg",
            "current_price": "Price",
            "market_value": "Value",
            "gain_loss_pct": "P/L %",
            "weight": "Weight %",
            "target_weight": "Target %",
            "sector": "Sector",
        }
    )
    st.dataframe(show, use_container_width=True, hide_index=True, height=height)


def action_cards(limit=5):
    actions = rebalance_actions(df)
    if actions.empty:
        st.info("No actions yet.")
        return
    for _, row in actions.head(limit).iterrows():
        ticker = row["ticker"]
        action = row["action"]
        drift = float(row["weight"] - row["target_weight"])
        badge, color = "HOLD", "muted"
        if "Add" in action:
            badge, color = "ADD", "green"
        elif "Stop" in action:
            badge, color = "STOP", "red"
        st.markdown(
            f"""
<div class="action-card">
  <strong>{ticker}</strong> <span class="{color}">{badge}</span><br>
  <span class="muted">{action} · drift {drift:.1f}%</span>
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


# ---------- contextual sidebar ----------
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
        with st.form("side_holding_form"):
            ticker = st.text_input("Ticker", value="TSM").upper().strip()
            name = st.text_input("Name", value="Taiwan Semiconductor ADR")
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
            avg_cost = st.number_input("Average Cost", min_value=0.0, value=0.0, step=1.0)
            target_weight = st.number_input("Target %", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
            sector = st.text_input("Sector", value="Semiconductors")
            asset_type = st.selectbox("Type", ["Stock", "ETF", "Cash", "Crypto", "Other"])
            if st.form_submit_button("Save holding", use_container_width=True) and ticker:
                upsert_holding(ticker, name, shares, avg_cost, target_weight, asset_type, sector)
                st.success(f"Saved {ticker}")
                st.rerun()

        candidates = [t for t in df["ticker"].tolist() if t != "CASH"] if not df.empty else []
        if candidates:
            st.divider()
            del_ticker = st.selectbox("Delete", candidates)
            if st.button("Delete holding", use_container_width=True):
                delete_holding(del_ticker)
                st.rerun()

    elif nav == "Transactions":
        st.caption("Record Transaction")
        with st.form("side_tx_form"):
            tx_date = st.date_input("Date", value=date.today())
            ticker = st.text_input("Ticker", value="TSM").upper().strip()
            action = st.selectbox("Action", ["BUY", "SELL", "DIVIDEND", "CASH_IN", "CASH_OUT"])
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
            price = st.number_input("Price / Amount", min_value=0.0, value=0.0, step=1.0)
            fees = st.number_input("Fees", min_value=0.0, value=0.0, step=0.1)
            note = st.text_input("Note", value="")
            if st.form_submit_button("Save transaction", use_container_width=True) and ticker:
                add_transaction(tx_date, ticker, action, shares, price, fees, note)
                st.success("Saved")
                st.rerun()

    elif nav == "Watchlist":
        st.caption("Add / Edit Watchlist")
        with st.form("side_watch_form"):
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
            seed_default_data()
            st.success("Database initialized")
        st.info("On Streamlit Cloud, database storage may reset after redeploy. Keep important records backed up.")


# ---------- pages ----------
if nav == "Dashboard":
    top_left, top_right = st.columns([1, 0.18])
    with top_right:
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    kpi_row()
    left, right = st.columns([1.45, 1], gap="medium")
    with left:
        st.subheader("Holdings")
        compact_holdings_table(230)
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

elif nav == "Portfolio":
    st.subheader("Portfolio")
    compact_holdings_table(430, full=True)

elif nav == "Transactions":
    st.subheader("Transactions")
    st.dataframe(get_transactions(), use_container_width=True, hide_index=True, height=470)

elif nav == "Watchlist":
    st.subheader("Watchlist")
    wdf = get_watchlist()
    if wdf.empty:
        st.info("No watchlist yet.")
    else:
        keep = ["ticker", "name", "current_price", "fair_value", "target_buy_price", "conviction", "score"]
        show = wdf[keep].rename(
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
    st.subheader("Settings")
    st.write("Use this page for database maintenance and deployment notes.")
    st.code("streamlit run app.py")
