import html

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
  --bg:#050505; --panel:#101010; --panel2:#151515; --line:#2b2b2b;
  --text:#f5f5f5; --muted:#9a9a9a; --soft:#d4d4d4; --dim:#737373;
}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none !important;}
[data-testid="stAppViewContainer"] {background:var(--bg);}
.block-container {padding:.45rem .8rem .7rem .8rem; max-width:1380px;}
h1 {font-size:1.08rem !important; margin:0 0 .1rem 0 !important; letter-spacing:-.035em; color:var(--text);}
h2 {font-size:.92rem !important; margin:.22rem 0 .18rem 0 !important; letter-spacing:-.02em;}
h3 {font-size:.78rem !important; margin:.2rem 0 .15rem 0 !important; color:var(--soft);}
hr {border-color:var(--line); margin:.42rem 0;}
.stDataFrame {border:1px solid var(--line); border-radius:12px; overflow:hidden;}
[data-testid="stMetric"] {background:var(--panel); border:1px solid var(--line); border-radius:13px; padding:7px 10px;}
[data-testid="stMetricLabel"] {font-size:.66rem; color:var(--muted);}
[data-testid="stMetricValue"] {font-size:.9rem; color:var(--text);}
button[kind="secondary"], button[kind="primary"] {border-radius:10px !important; min-height:33px; border-color:var(--line) !important;}
input, textarea, select {border-radius:10px !important;}
.muted {color:var(--muted); font-size:.74rem;}
.tiny {color:var(--muted); font-size:.66rem;}
.section-title {font-size:.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:.095em; margin:.05rem 0 .28rem 0;}
.card {background:var(--panel); border:1px solid var(--line); border-radius:15px; padding:11px 13px; margin-bottom:8px;}
.card-compact {background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:8px 10px; margin-bottom:6px;}
.focus-card {background:#f5f5f5; color:#050505; border:1px solid #f5f5f5; border-radius:16px; padding:13px 15px; margin-bottom:8px;}
.focus-card .muted, .focus-card .tiny {color:#525252;}
.focus-card hr {border-color:#d4d4d4;}
.row-card {display:grid; grid-template-columns:76px 1fr 74px; gap:10px; align-items:start; background:var(--panel); border:1px solid var(--line); border-radius:13px; padding:9px 10px; margin-bottom:6px;}
.row-card.dim {opacity:.72;}
.row-title {font-weight:700; color:var(--text); font-size:.84rem;}
.row-sub {color:var(--muted); font-size:.7rem; margin-top:2px;}
.level {font-weight:800; font-size:.68rem; letter-spacing:.02em; border:1px solid var(--line); padding:3px 7px; border-radius:999px; display:inline-block; color:var(--soft);}
.level.ready {background:#f5f5f5; color:#050505; border-color:#f5f5f5;}
.level.review {background:#d4d4d4; color:#050505; border-color:#d4d4d4;}
.level.wait {background:#161616; color:#9a9a9a;}
.label {color:var(--muted); font-size:.66rem; text-transform:uppercase; letter-spacing:.08em;}
.value {font-weight:700; color:var(--text); font-size:.82rem;}
.guide {display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; margin-bottom:8px;}
.guide-item {background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:8px 9px; min-height:56px;}
.guide-item b {font-size:.72rem; color:var(--soft);}
.guide-item div {font-size:.66rem; color:var(--muted); margin-top:3px; line-height:1.25;}
.soft-line {height:1px; background:var(--line); margin:8px 0;}
</style>
""",
    unsafe_allow_html=True,
)


def esc(value) -> str:
    return html.escape(str(value))


def refresh_all():
    refresh_prices()


def decision_copy(decision: str) -> str:
    return {
        "READY": "actionable today",
        "REVIEW": "watch closely",
        "WAIT": "skip for now",
    }.get(str(decision).upper(), "review")


def setup_copy(setup: str) -> str:
    setup_l = str(setup or "").lower()
    if "pullback" in setup_l or "continuation" in setup_l:
        return "ย่อ/พักตัวในเทรนด์ที่ยังดี มีแผนเข้าใกล้ Buy Trigger"
    if "breakout" in setup_l:
        return "รอทะลุแนวต้านและยืนได้ก่อน ไม่ซื้อก่อน confirmation"
    if "wait for pullback" in setup_l:
        return "หุ้นยังน่าสนใจ แต่ราคายืดเกิน รอให้ย่อก่อน"
    if "no clean" in setup_l:
        return "ยังไม่มีจุดเข้าที่คุมความเสี่ยงได้ดีพอ"
    return "ใช้เป็นระดับอ้างอิง ต้องเช็กกราฟก่อนตัดสินใจ"


def trade_card(row, muted=False):
    ticker = esc(row.get("Ticker", ""))
    decision = esc(row.get("Decision", "WAIT"))
    score = row.get("Score", 0)
    price = row.get("Price", 0)
    entry = row.get("Entry", 0)
    stop = row.get("Stop", 0)
    target = row.get("Target", 0)
    rr = row.get("R/R", 0)
    setup = esc(row.get("Setup", ""))
    reason = esc(row.get("Reason", ""))
    level_class = str(decision).lower()
    css_dim = " dim" if muted else ""
    trigger_label = "Buy Trigger" if decision != "WAIT" else "Ref. Trigger"
    st.markdown(
        f"""
<div class="row-card{css_dim}">
  <div>
    <div class="row-title">{ticker}</div>
    <div class="level {level_class}">{decision}</div>
  </div>
  <div>
    <div><span class="value">{setup}</span></div>
    <div class="row-sub">{setup_copy(setup)}</div>
    <div class="row-sub">{reason}</div>
    <div class="soft-line"></div>
    <div class="row-sub">Price {usd(price)} · {trigger_label} {usd(entry)} · Stop {usd(stop)} · Target {usd(target)}</div>
  </div>
  <div style="text-align:right;">
    <div class="label">Score</div>
    <div class="value">{score}/100</div>
    <div class="row-sub">{rr}R</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def holdings_view(df, height=235):
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


def manage_watchlist_inline():
    with st.expander("Manage watchlist", expanded=False):
        c1, c2, c3 = st.columns([1, .5, 1.5])
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


def manage_holdings_inline(holdings):
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


holdings = get_enriched_holdings()
summary = portfolio_summary()
last_sync = get_setting("last_price_sync", "Not synced yet")

header_left, header_mid, header_right = st.columns([1.2, 2.1, .65])
with header_left:
    st.title("Portfolio Desk")
with header_mid:
    st.caption(f"One-page decision desk · Last sync: {last_sync}")
with header_right:
    if st.button("Refresh", use_container_width=True):
        refresh_all()
        st.rerun()

left, right = st.columns([1.08, .92], gap="medium")

with left:
    st.markdown('<div class="section-title">Daily Desk</div>', unsafe_allow_html=True)
    desk = trade_desk_watchlist()

    st.markdown(
        """
<div class="guide">
  <div class="guide-item"><b>READY</b><div>Setup ใช้ได้แล้ว เช็กขนาดไม้ก่อนเข้า</div></div>
  <div class="guide-item"><b>REVIEW</b><div>น่าสนใจ แต่รอจังหวะ/confirmation</div></div>
  <div class="guide-item"><b>WAIT</b><div>ข้ามก่อน ยังไม่มี edge ชัด</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    if desk.empty:
        st.markdown(
            """
<div class="card">
  <h2>No watchlist yet</h2>
  <div class="muted">Add stocks you want the system to monitor. The desk will suggest Buy Trigger / Stop / Target automatically.</div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        actionable = desk[desk["Decision"].isin(["READY", "REVIEW"])].copy()
        skip = desk[desk["Decision"] == "WAIT"].copy()
        best = actionable.iloc[0] if not actionable.empty else desk.iloc[0]
        decision = str(best["Decision"])
        focus_line = {
            "READY": "Actionable setup. Only proceed if position size and portfolio risk are acceptable.",
            "REVIEW": "Close to actionable. Watch this first and wait for confirmation or a better trigger.",
            "WAIT": "No clean edge today. Keep it on the list but do not force the trade.",
        }.get(decision, "Review setup before acting.")
        trigger_label = "Buy Trigger" if decision != "WAIT" else "Reference Trigger"

        st.markdown(
            f"""
<div class="focus-card">
  <div class="tiny">TODAY'S FOCUS</div>
  <h2>{esc(best['Ticker'])} <span class="level {decision.lower()}">{decision}</span></h2>
  <div>{trigger_label} <b>{usd(best['Entry'])}</b> · Stop <b>{usd(best['Stop'])}</b> · Target <b>{usd(best['Target'])}</b></div>
  <div class="muted">{esc(best['Setup'])} · Score {best['Score']}/100 · R/R {best['R/R']}R</div>
  <hr>
  <div class="muted">{focus_line}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title">Focus Today</div>', unsafe_allow_html=True)
        if actionable.empty:
            st.markdown("<div class='card-compact muted'>No actionable setups today. Best action is to wait.</div>", unsafe_allow_html=True)
        else:
            for _, row in actionable.head(3).iterrows():
                trade_card(row)

        st.markdown('<div class="section-title">Skip Today</div>', unsafe_allow_html=True)
        if skip.empty:
            st.markdown("<div class='card-compact muted'>No skip list right now.</div>", unsafe_allow_html=True)
        else:
            for _, row in skip.head(4).iterrows():
                trade_card(row, muted=True)

    manage_watchlist_inline()

with right:
    st.markdown('<div class="section-title">Dashboard</div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Portfolio", usd(summary["total_value"]))
    k2.metric("P/L", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    k3.metric("Positions", str(summary["positions"]), summary["risk_label"])

    st.markdown('<div class="section-title">Holdings</div>', unsafe_allow_html=True)
    holdings_view(holdings, height=228)

    lower_left, lower_right = st.columns([1, .9], gap="small")
    with lower_left:
        st.markdown('<div class="section-title">Risk Notes</div>', unsafe_allow_html=True)
        for note in top_risk_notes(holdings)[:3]:
            st.markdown(f"<div class='card-compact'>{esc(note)}</div>", unsafe_allow_html=True)
    with lower_right:
        st.markdown('<div class="section-title">Allocation</div>', unsafe_allow_html=True)
        st.plotly_chart(allocation_chart(holdings), use_container_width=True)

    manage_holdings_inline(holdings)
