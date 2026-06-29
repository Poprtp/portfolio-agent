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

st.set_page_config(page_title="Portfolio Desk", page_icon="▣", layout="wide", initial_sidebar_state="collapsed")
init_db()

st.markdown(
    """
<style>
:root {
  --bg:#050505; --panel:#101010; --panel2:#151515; --line:#2a2a2a;
  --text:#f5f5f5; --muted:#9a9a9a; --soft:#d4d4d4;
}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none !important;}
[data-testid="stAppViewContainer"] {background:var(--bg);}
.block-container {padding:.55rem .85rem .8rem .85rem; max-width:1380px;}
h1 {font-size:1.15rem !important; margin:0 0 .2rem 0 !important; letter-spacing:-.035em; color:var(--text);}
h2 {font-size:.95rem !important; margin:.3rem 0 .25rem 0 !important; letter-spacing:-.02em;}
h3 {font-size:.82rem !important; margin:.25rem 0 .18rem 0 !important; color:var(--soft);}
hr {border-color:var(--line); margin:.45rem 0;}
.stDataFrame {border:1px solid var(--line); border-radius:12px; overflow:hidden;}
[data-testid="stMetric"] {background:var(--panel); border:1px solid var(--line); border-radius:13px; padding:8px 10px;}
[data-testid="stMetricLabel"] {font-size:.68rem; color:var(--muted);}
[data-testid="stMetricValue"] {font-size:.95rem; color:var(--text);}
button[kind="secondary"], button[kind="primary"] {border-radius:10px !important; min-height:34px; border-color:var(--line) !important;}
input, textarea, select {border-radius:10px !important;}
.muted {color:var(--muted); font-size:.76rem;}
.tiny {color:var(--muted); font-size:.68rem;}
.section-title {font-size:.76rem; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:.25rem;}
.card {background:var(--panel); border:1px solid var(--line); border-radius:15px; padding:12px 14px; margin-bottom:10px;}
.card-compact {background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:9px 11px; margin-bottom:7px;}
.focus-card {background:#f5f5f5; color:#050505; border:1px solid #f5f5f5; border-radius:16px; padding:14px 16px; margin-bottom:10px;}
.focus-card .muted, .focus-card .tiny {color:#525252;}
.pill {display:inline-block; border:1px solid var(--line); border-radius:999px; padding:2px 8px; color:var(--soft); font-size:.7rem; margin-left:4px;}
.pill-solid {display:inline-block; background:#f5f5f5; color:#050505; border-radius:999px; padding:2px 8px; font-size:.7rem; font-weight:700; margin-left:4px;}
.level-ready, .level-review, .level-wait {color:#f5f5f5; font-weight:700;}
.compact-expander [data-testid="stExpander"] {border-color:var(--line); background:var(--panel);}
</style>
""",
    unsafe_allow_html=True,
)


def refresh_all():
    refresh_prices()


holdings = get_enriched_holdings()
summary = portfolio_summary()
last_sync = get_setting("last_price_sync", "Not synced yet")

header_left, header_mid, header_right = st.columns([1.3, 2.1, .7])
with header_left:
    st.title("Portfolio Desk")
with header_mid:
    st.caption(f"One-page trade focus · Last sync: {last_sync}")
with header_right:
    if st.button("Refresh", use_container_width=True):
        refresh_all()
        st.rerun()

left, right = st.columns([1.05, .95], gap="medium")


def holdings_view(df, height=250):
    if df.empty:
        st.info("No holdings yet.")
        return
    show = df[["ticker", "shares", "avg_cost", "current_price", "market_value", "gain_loss", "gain_loss_pct"]].copy()
    show = show.rename(
        columns={
            "ticker": "Ticker",
            "shares": "Shares",
            "avg_cost": "Avg",
            "current_price": "Price",
            "market_value": "Value",
            "gain_loss": "P/L",
            "gain_loss_pct": "P/L %",
        }
    )
    st.dataframe(show, use_container_width=True, hide_index=True, height=height)


def compact_watchlist_table(df, height=245):
    if df.empty:
        st.info("Add tickers to the watchlist.")
        return
    show = df[["Ticker", "Decision", "Score", "Price", "Entry", "Stop", "Target", "R/R", "Setup"]].copy()
    st.dataframe(show, use_container_width=True, hide_index=True, height=height)


def manage_watchlist_inline():
    with st.expander("Manage watchlist", expanded=False):
        c1, c2, c3 = st.columns([1, .55, 1.45])
        with c1:
            ticker = st.text_input("Ticker", value="MSFT", key="watch_ticker").upper().strip()
        with c2:
            st.write("")
            st.write("")
            if st.button("Add", use_container_width=True) and ticker:
                add_watchlist(ticker)
                st.rerun()
        with c3:
            wdf = get_watchlist()
            if not wdf.empty:
                del_ticker = st.selectbox("Remove", wdf["ticker"].tolist(), key="delete_watch")
                if st.button("Remove", use_container_width=True):
                    delete_watchlist(del_ticker)
                    st.rerun()


def manage_holdings_inline():
    with st.expander("Manage holdings", expanded=False):
        c1, c2, c3, c4 = st.columns([.8, .65, .75, .75])
        with c1:
            ticker = st.text_input("Ticker", value="TSM", key="hold_ticker").upper().strip()
        with c2:
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0, key="hold_shares")
        with c3:
            avg = st.number_input("Avg Cost", min_value=0.0, value=0.0, step=1.0, key="hold_avg")
        with c4:
            st.write("")
            st.write("")
            if st.button("Save", use_container_width=True) and ticker:
                upsert_holding_auto(ticker, shares, avg)
                st.rerun()

        if not holdings.empty:
            d1, d2 = st.columns([1, .75])
            with d1:
                del_ticker = st.selectbox("Delete holding", holdings["ticker"].tolist(), key="delete_holding")
            with d2:
                st.write("")
                st.write("")
                if st.button("Delete", use_container_width=True):
                    delete_holding(del_ticker)
                    st.rerun()


with left:
    st.markdown('<div class="section-title">Daily Desk</div>', unsafe_allow_html=True)
    desk = trade_desk_watchlist()

    if desk.empty:
        st.markdown(
            """
<div class="card">
  <h2>No watchlist yet</h2>
  <div class="muted">Add stocks you want the system to monitor. The desk will suggest Entry / Stop / Target automatically.</div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        best = desk.iloc[0]
        decision = str(best["Decision"])
        if decision == "READY":
            focus_line = "Actionable setup. Check execution size before buying."
        elif decision == "REVIEW":
            focus_line = "Close to actionable. Wait for confirmation or better entry."
        else:
            focus_line = "Not ready. Do not force the trade."

        st.markdown(
            f"""
<div class="focus-card">
  <div class="tiny">TODAY'S FOCUS</div>
  <h2>{best['Ticker']} <span class="pill-solid">{decision}</span></h2>
  <div>Entry <b>{usd(best['Entry'])}</b> · Stop <b>{usd(best['Stop'])}</b> · Target <b>{usd(best['Target'])}</b></div>
  <div class="muted">{best['Setup']} · Score {best['Score']}/100 · R/R {best['R/R']}R</div>
  <hr style="border-color:#d4d4d4; margin:.5rem 0;">
  <div class="muted">{focus_line}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    ready_count = 0 if desk.empty else int((desk["Decision"] == "READY").sum())
    review_count = 0 if desk.empty else int((desk["Decision"] == "REVIEW").sum())
    wait_count = 0 if desk.empty else int((desk["Decision"] == "WAIT").sum())
    a, b, c = st.columns(3)
    a.metric("Ready", ready_count)
    b.metric("Review", review_count)
    c.metric("Wait", wait_count)

    st.markdown('<div class="section-title">Watchlist setups</div>', unsafe_allow_html=True)
    compact_watchlist_table(desk)
    manage_watchlist_inline()

with right:
    st.markdown('<div class="section-title">Dashboard</div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Portfolio", usd(summary["total_value"]))
    k2.metric("P/L", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    k3.metric("Positions", str(summary["positions"]), summary["risk_label"])

    st.markdown('<div class="section-title">Holdings</div>', unsafe_allow_html=True)
    holdings_view(holdings, height=245)

    lower_left, lower_right = st.columns([1, .9], gap="small")
    with lower_left:
        st.markdown('<div class="section-title">Risk notes</div>', unsafe_allow_html=True)
        for note in top_risk_notes(holdings)[:3]:
            st.markdown(f"<div class='card-compact'>{note}</div>", unsafe_allow_html=True)
    with lower_right:
        st.markdown('<div class="section-title">Allocation</div>', unsafe_allow_html=True)
        st.plotly_chart(allocation_chart(holdings), use_container_width=True)

    manage_holdings_inline()
