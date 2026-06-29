import streamlit as st

from services.database import get_setting, init_db
from services.portfolio import (
    delete_holding,
    get_enriched_holdings,
    portfolio_summary,
    refresh_prices,
    top_risk_notes,
    upsert_holding_auto,
)
from services.watchlist import add_watchlist, delete_watchlist, get_watchlist, trade_desk_watchlist
from utils.charts import allocation_chart
from utils.formatting import pct, usd

st.set_page_config(page_title="AI Portfolio OS", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
init_db()

st.markdown(
    """
<style>
[data-testid="stSidebar"] {display:none !important;}
[data-testid="collapsedControl"] {display:none !important;}
.block-container {padding: .75rem 1.15rem 1rem 1.15rem; max-width: 1180px;}
h1 {font-size: 1.28rem !important; margin: 0 0 .35rem 0 !important; letter-spacing:-.03em;}
h2 {font-size: 1.0rem !important; margin: .45rem 0 .25rem 0 !important;}
h3 {font-size: .9rem !important; margin: .35rem 0 .2rem 0 !important;}
[data-testid="stMetric"] {background:#111827; border:1px solid #1f2937; border-radius:14px; padding:10px 12px;}
[data-testid="stMetricLabel"] {font-size:.72rem; color:#9ca3af;}
[data-testid="stMetricValue"] {font-size:1.05rem;}
.stDataFrame {border:1px solid #1f2937; border-radius:12px; overflow:hidden;}
.focus-card {background:#111827; border:1px solid #1f2937; border-radius:14px; padding:13px 15px; min-height:118px;}
.small-card {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:10px 12px; margin-bottom:8px;}
.green {color:#22c55e;} .red {color:#ef4444;} .yellow {color:#facc15;} .muted {color:#9ca3af;} .blue {color:#60a5fa;}
button[kind="secondary"], button[kind="primary"] {border-radius:10px !important; min-height:38px;}
hr {border-color:#1f2937; margin:.6rem 0;}
</style>
""",
    unsafe_allow_html=True,
)

PAGES = ["Daily Desk", "Dashboard", "Settings"]
if "page" not in st.session_state:
    st.session_state.page = "Daily Desk"
nav = st.session_state.page


def set_page(page):
    st.session_state.page = page
    st.rerun()


def refresh_all():
    refresh_prices()
    # Trade desk computes latest setups on demand via yfinance.


holdings = get_enriched_holdings()
summary = portfolio_summary()

st.title("AI Portfolio OS")
cols = st.columns([.85, .85, .8, 3.8, .8])
for i, page in enumerate(PAGES):
    with cols[i]:
        if st.button(page, use_container_width=True, type="primary" if page == nav else "secondary"):
            set_page(page)
with cols[-1]:
    if st.button("Refresh", use_container_width=True):
        refresh_all()
        st.rerun()

last_sync = get_setting("last_price_sync", "Not synced yet")
st.caption(f"Last sync: {last_sync}")


def holdings_view(df, height=240):
    if df.empty:
        st.info("No holdings yet. Add your first ticker in Dashboard.")
        return
    show = df[["ticker", "shares", "avg_cost", "current_price", "market_value", "gain_loss", "gain_loss_pct", "weight"]].copy()
    show = show.rename(
        columns={
            "ticker": "Ticker",
            "shares": "Shares",
            "avg_cost": "Avg",
            "current_price": "Price",
            "market_value": "Value",
            "gain_loss": "P/L",
            "gain_loss_pct": "P/L %",
            "weight": "Weight %",
        }
    )
    st.dataframe(show, use_container_width=True, hide_index=True, height=height)


def manage_holdings():
    with st.expander("Add / update / delete holding", expanded=False):
        c1, c2, c3, c4 = st.columns([1, .8, .8, 1])
        with c1:
            ticker = st.text_input("Ticker", value="TSM", key="hold_ticker").upper().strip()
        with c2:
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0, key="hold_shares")
        with c3:
            avg = st.number_input("Average Cost", min_value=0.0, value=0.0, step=1.0, key="hold_avg")
        with c4:
            st.write("")
            st.write("")
            if st.button("Save holding", use_container_width=True) and ticker:
                upsert_holding_auto(ticker, shares, avg)
                st.rerun()

        if not holdings.empty:
            d1, d2 = st.columns([1, 4])
            with d1:
                del_ticker = st.selectbox("Delete", holdings["ticker"].tolist(), key="delete_holding")
            with d2:
                st.write("")
                st.write("")
                if st.button("Delete holding", use_container_width=False):
                    delete_holding(del_ticker)
                    st.rerun()


def watchlist_manager():
    with st.expander("Add / remove watchlist", expanded=False):
        c1, c2, c3 = st.columns([1, .8, 3])
        with c1:
            ticker = st.text_input("Ticker", value="MSFT", key="watch_ticker").upper().strip()
        with c2:
            st.write("")
            st.write("")
            if st.button("Add", use_container_width=True) and ticker:
                add_watchlist(ticker)
                st.rerun()
        wdf = get_watchlist()
        if not wdf.empty:
            with c3:
                del_ticker = st.selectbox("Remove", wdf["ticker"].tolist(), key="delete_watch")
                if st.button("Remove from watchlist"):
                    delete_watchlist(del_ticker)
                    st.rerun()


def decision_color(decision):
    return "green" if decision == "READY" else "yellow" if decision == "REVIEW" else "red"


if nav == "Daily Desk":
    st.caption("One-page trading focus. The system highlights what matters and hides the rest.")
    desk = trade_desk_watchlist()

    if desk.empty:
        st.info("Add tickers to your watchlist first.")
        watchlist_manager()
    else:
        best = desk.iloc[0]
        ready_count = int((desk["Decision"] == "READY").sum())
        review_count = int((desk["Decision"] == "REVIEW").sum())
        wait_count = int((desk["Decision"] == "WAIT").sum())

        c1, c2, c3 = st.columns([1.15, 1, 1], gap="medium")
        with c1:
            color = decision_color(best["Decision"])
            st.markdown(
                f"""
<div class="focus-card">
  <span class="muted">Focus Today</span><br>
  <h2>{best['Ticker']} <span class="{color}">{best['Decision']}</span></h2>
  <div>Entry <b>{usd(best['Entry'])}</b> · Stop <b>{usd(best['Stop'])}</b> · Target <b>{usd(best['Target'])}</b></div>
  <div class="muted">{best['Setup']} · Score {best['Score']}/100 · R/R {best['R/R']}R</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
<div class="focus-card">
  <span class="muted">Market Discipline</span><br>
  <h2>{summary['risk_label']} Risk</h2>
  <div class="muted">Do not chase price. Only trade setups with clear Entry / Stop / Target.</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
<div class="focus-card">
  <span class="muted">Watchlist Status</span><br>
  <h2>{ready_count} Ready · {review_count} Review</h2>
  <div class="muted">{wait_count} waiting. Focus only on the highest-quality setup.</div>
</div>
""",
                unsafe_allow_html=True,
            )

        st.subheader("Watchlist Trade Setups")
        show = desk[["Ticker", "Decision", "Score", "Price", "Entry", "Stop", "Target", "R/R", "Setup", "Reason"]].copy()
        st.dataframe(show, use_container_width=True, hide_index=True, height=280)
        watchlist_manager()

elif nav == "Dashboard":
    st.caption("Portfolio summary and simple holdings management.")
    k1, k2, k3 = st.columns(3)
    k1.metric("Portfolio Value", usd(summary["total_value"]))
    k2.metric("Gain / Loss", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    k3.metric("Positions", str(summary["positions"]), summary["risk_label"])

    left, right = st.columns([1.4, .85], gap="medium")
    with left:
        st.subheader("Holdings")
        holdings_view(holdings, height=255)
    with right:
        st.subheader("Allocation")
        st.plotly_chart(allocation_chart(holdings), use_container_width=True)

    r1, r2 = st.columns([1, 1])
    with r1:
        st.subheader("What to watch")
        for note in top_risk_notes(holdings):
            st.markdown(f"<div class='small-card'>{note}</div>", unsafe_allow_html=True)
    with r2:
        manage_holdings()

elif nav == "Settings":
    st.caption("System tools")
    st.info("Background services run inside the app: SQLite storage, price refresh, portfolio calculations, and professional-style setup scoring.")
    if st.button("Repair database"):
        init_db()
        st.success("Database repaired.")
