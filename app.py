import html

import streamlit as st

from services.advisor import ai_advisor
from services.alerts import decision_alerts
from services.database import get_setting, init_db
from services.history import get_last_call_performance, save_daily_snapshot
from services.journal import get_trade_journal, save_planned_trade, update_trade_status
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

st.set_page_config(page_title="Portfolio Desk", page_icon="▣", layout="wide", initial_sidebar_state="expanded")
init_db()

st.markdown(
    """
<style>
:root {
  --bg:#050505; --panel:#101010; --panel2:#151515; --panel3:#1d1d1d; --line:#2b2b2b;
  --text:#f5f5f5; --muted:#9a9a9a; --soft:#d4d4d4; --dim:#737373;
}
[data-testid="stAppViewContainer"] {background:var(--bg);}
[data-testid="stSidebar"] {background:#080808; border-right:1px solid var(--line);}
[data-testid="stSidebar"] .block-container {padding:.8rem .7rem;}
.block-container {padding:.55rem .85rem .75rem .85rem; max-width:1420px;}
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
.guide {display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; margin-bottom:8px;}
.guide-item {background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:8px 9px; min-height:56px;}
.guide-item b {font-size:.72rem; color:var(--soft);}
.guide-item div {font-size:.66rem; color:var(--muted); margin-top:3px; line-height:1.25;}
.level {font-weight:800; font-size:.68rem; letter-spacing:.02em; border:1px solid var(--line); padding:3px 7px; border-radius:999px; display:inline-block; color:var(--soft);}
.level.ready {background:#f5f5f5; color:#050505; border-color:#f5f5f5;}
.level.review {background:#d4d4d4; color:#050505; border-color:#d4d4d4;}
.level.wait {background:#161616; color:#9a9a9a;}
.label {color:var(--muted); font-size:.66rem; text-transform:uppercase; letter-spacing:.08em;}
.value {font-weight:700; color:var(--text); font-size:.82rem;}
.homework-grid {display:grid; grid-template-columns:repeat(5, 1fr); gap:6px; margin:.35rem 0 .4rem 0;}
.homework-item {background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:7px 8px; min-height:54px;}
.homework-item b {display:block; color:var(--soft); font-size:.72rem; margin-top:1px;}
.homework-item span {color:var(--muted); font-size:.62rem; text-transform:uppercase; letter-spacing:.06em;}
.trigger-grid {display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; margin:.35rem 0;}
.trigger-item {background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:7px 8px;}
.trigger-item b {font-size:.76rem; color:var(--text);}
.trigger-item span {display:block; color:var(--muted); font-size:.62rem; text-transform:uppercase; letter-spacing:.06em;}
.reason-box {background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:8px 10px; color:var(--muted); font-size:.72rem; margin-top:6px;}
.mini-list {font-size:.72rem; color:var(--muted); line-height:1.4; white-space:pre-line;}
[data-testid="stExpander"] {border:1px solid var(--line) !important; border-radius:13px !important; background:var(--panel) !important; margin-bottom:7px !important;}
[data-testid="stExpander"] details summary {font-size:.80rem !important; font-weight:700 !important; color:var(--text) !important; padding:5px 4px !important;}
[data-testid="stExpander"] details[open] summary {border-bottom:1px solid var(--line);}
.sidebar-note {font-size:.7rem; color:var(--muted); line-height:1.35;}
</style>
""",
    unsafe_allow_html=True,
)


def esc(value) -> str:
    return html.escape(str(value))


def refresh_all():
    refresh_prices()
    try:
        st.cache_data.clear()
    except Exception:
        pass


def get_openai_key() -> str:
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""


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


def decision_line(decision: str) -> str:
    return {
        "READY": "Setup ใช้ได้แล้ว เช็กขนาดไม้และความเสี่ยงก่อนเข้า",
        "REVIEW": "น่าสนใจ แต่รอจังหวะหรือ confirmation เพิ่ม",
        "WAIT": "ข้ามก่อน ยังไม่มี edge ชัดพอสำหรับวันนี้",
    }.get(str(decision).upper(), "Review setup before acting")


def compact_trade_expander(row, portfolio_value: float, expanded=False):
    ticker = str(row.get("Ticker", ""))
    decision = str(row.get("Decision", "WAIT"))
    score = int(row.get("Score", 0) or 0)
    setup = str(row.get("Setup", ""))
    level_icon = "●" if decision == "READY" else "◐" if decision == "REVIEW" else "○"
    header = f"{level_icon} {ticker} · {decision} · Score {score}/100"

    with st.expander(header, expanded=expanded):
        trigger_label = "Buy Trigger" if decision != "WAIT" else "Reference Trigger"
        st.markdown(
            f"""
<div class="trigger-grid">
  <div class="trigger-item"><span>Current</span><b>{usd(row.get('Price', 0))}</b></div>
  <div class="trigger-item"><span>{trigger_label}</span><b>{usd(row.get('Entry', 0))}</b></div>
  <div class="trigger-item"><span>Stop</span><b>{usd(row.get('Stop', 0))}</b></div>
  <div class="trigger-item"><span>Target</span><b>{usd(row.get('Target', 0))}</b></div>
</div>
<div class="reason-box">
  <b style="color:#f5f5f5;">{esc(setup)}</b><br>
  {esc(setup_copy(setup))}<br>
  <span class="muted">R/R {row.get('R/R', 0)}R · Technical {row.get('Technical Score', row.get('Score', 0))}/100 · Homework {row.get('Homework Score', 0)}/100</span>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
<div class="homework-grid">
  <div class="homework-item"><span>Business</span><b>{esc(row.get('Business', 'Unknown'))}</b></div>
  <div class="homework-item"><span>Growth</span><b>{esc(row.get('Growth', 'Unknown'))}</b></div>
  <div class="homework-item"><span>Profit</span><b>{esc(row.get('Profit', 'Unknown'))}</b></div>
  <div class="homework-item"><span>Valuation</span><b>{esc(row.get('Valuation', 'Unknown'))}</b></div>
  <div class="homework-item"><span>Exit</span><b>{esc(row.get('Exit', 'Stop/Thesis'))}</b></div>
</div>
<div class="reason-box">{esc(row.get('Reason', ''))}</div>
""",
            unsafe_allow_html=True,
        )

        p1, p2 = st.columns([.75, 1.25])
        with p1:
            if st.button("Plan trade", use_container_width=True, key=f"plan_{ticker}"):
                trade_id = save_planned_trade(dict(row), portfolio_value)
                st.session_state.last_trade_action = f"Saved {ticker} as planned trade #{trade_id}"
                st.rerun()
        with p2:
            st.caption("Position size is calculated at 1% portfolio risk in Trade Journal.")


def render_stock_grid(df, portfolio_value: float, expanded_first=False):
    if df.empty:
        return
    cols = st.columns(2, gap="small")
    for i, (_, row) in enumerate(df.iterrows()):
        with cols[i % 2]:
            compact_trade_expander(row, portfolio_value, expanded=(expanded_first and i == 0))


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


def manage_watchlist_sidebar():
    st.markdown("### Watchlist")
    st.markdown("<div class='sidebar-note'>เพิ่ม/ลบหุ้นที่ต้องการให้ Daily Desk วิเคราะห์</div>", unsafe_allow_html=True)
    if "last_watch_action" in st.session_state:
        st.caption(st.session_state.last_watch_action)

    with st.form("add_watch_form", clear_on_submit=True):
        ticker = st.text_input("Add ticker", value="", placeholder="e.g. CRWD, AMD, TSM").upper().strip()
        add_clicked = st.form_submit_button("Add to Watchlist", use_container_width=True)
        if add_clicked:
            if ticker:
                add_watchlist(ticker)
                st.session_state.last_watch_action = f"Added {ticker}"
                st.rerun()
            else:
                st.error("Please enter a ticker.")

    wdf = get_watchlist()
    st.caption(f"Watchlist: {len(wdf)} symbols")
    if not wdf.empty:
        with st.form("delete_watch_form"):
            del_ticker = st.selectbox("Remove ticker", wdf["ticker"].tolist(), key="delete_watch")
            remove_clicked = st.form_submit_button("Remove", use_container_width=True)
            if remove_clicked:
                delete_watchlist(del_ticker)
                st.session_state.last_watch_action = f"Removed {del_ticker}"
                st.rerun()

    st.divider()
    st.caption("Default baseline includes 50 Nasdaq-100 / QQQ-style large-cap names. Remove any ticker you do not want to track.")


def manage_holdings_inline(holdings):
    with st.expander("Manage holdings", expanded=False):
        if "last_hold_action" in st.session_state:
            st.caption(st.session_state.last_hold_action)
        with st.form("holdings_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([.85, .7, .8, .65])
            with c1:
                ticker = st.text_input("Ticker", value="", placeholder="e.g. RKLB").upper().strip()
            with c2:
                shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
            with c3:
                avg = st.number_input("Avg Cost", min_value=0.0, value=0.0, step=1.0)
            with c4:
                st.write("")
                save_clicked = st.form_submit_button("Save", use_container_width=True)
            if save_clicked:
                if not ticker:
                    st.error("Please enter a ticker.")
                elif shares <= 0 or avg <= 0:
                    st.error("Shares and Avg Cost must be greater than 0.")
                else:
                    upsert_holding_auto(ticker, shares, avg)
                    st.session_state.last_hold_action = f"Saved {ticker} holding"
                    st.rerun()

        if not holdings.empty:
            with st.form("delete_holdings_form"):
                d1, d2 = st.columns([1.4, .65])
                with d1:
                    del_ticker = st.selectbox("Delete holding", holdings["ticker"].tolist(), key="delete_holding")
                with d2:
                    st.write("")
                    delete_clicked = st.form_submit_button("Delete", use_container_width=True)
                if delete_clicked:
                    delete_holding(del_ticker)
                    st.session_state.last_hold_action = f"Deleted {del_ticker} holding"
                    st.rerun()


def journal_panel():
    journal = get_trade_journal(limit=5)
    with st.expander("Trade Journal", expanded=False):
        if "last_trade_action" in st.session_state:
            st.caption(st.session_state.last_trade_action)
        if journal.empty:
            st.caption("No planned trades yet.")
            return
        for _, r in journal.iterrows():
            st.markdown(
                f"<div class='card-compact'><b>{esc(r['ticker'])}</b> · {esc(r['status'])} · {usd(r['entry'])} / {usd(r['stop'])} / {usd(r['target'])}<br><span class='muted'>Shares {int(r['shares'])} · Score {int(r['score'])}/100 · {esc(r['created_at'])}</span></div>",
                unsafe_allow_html=True,
            )
        ids = journal["id"].tolist()
        c1, c2 = st.columns([1, 1])
        with c1:
            trade_id = st.selectbox("Trade ID", ids)
        with c2:
            new_status = st.selectbox("Status", ["Planned", "Open", "Closed", "Cancelled"])
        if st.button("Update trade status", use_container_width=True):
            update_trade_status(trade_id, new_status)
            st.session_state.last_trade_action = f"Updated trade #{trade_id} to {new_status}"
            st.rerun()


holdings = get_enriched_holdings()
summary = portfolio_summary()
last_sync = get_setting("last_price_sync", "Not synced yet")

with st.sidebar:
    if st.button("Refresh Data", use_container_width=True):
        refresh_all()
        st.rerun()
    st.caption(f"Last sync: {last_sync}")
    scan_limit = st.slider("Analyze symbols", min_value=10, max_value=50, value=50, step=5)
    st.divider()
    manage_watchlist_sidebar()

left, right = st.columns([1.08, .92], gap="medium")

with left:
    st.markdown('<div class="section-title">Daily Desk</div>', unsafe_allow_html=True)
    desk = trade_desk_watchlist(limit=scan_limit)
    if not desk.empty:
        try:
            save_daily_snapshot(desk)
        except Exception:
            pass

    st.markdown(
        """
<div class="guide">
  <div class="guide-item"><b>READY</b><div>Setup ผ่านแล้ว แต่ยังต้องคุมขนาดไม้</div></div>
  <div class="guide-item"><b>REVIEW</b><div>น่าสนใจ รอจังหวะหรือ confirmation</div></div>
  <div class="guide-item"><b>WAIT</b><div>ข้ามก่อน ไม่มี edge ชัด</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    advisor_text = ai_advisor(desk, holdings, summary, get_openai_key())
    st.markdown(
        f"""
<div class="card">
  <div class="section-title">AI Advisor</div>
  <div class="mini-list">{esc(advisor_text)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if desk.empty:
        st.markdown(
            """
<div class="card">
  <h2>No watchlist yet</h2>
  <div class="muted">Add stocks in the sidebar. The desk will suggest Buy Trigger / Stop / Target automatically.</div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        actionable = desk[desk["Decision"].isin(["READY", "REVIEW"])].copy()
        skip = desk[desk["Decision"] == "WAIT"].copy()
        best = actionable.iloc[0] if not actionable.empty else desk.iloc[0]
        decision = str(best["Decision"])
        trigger_label = "Buy Trigger" if decision != "WAIT" else "Reference Trigger"

        st.markdown(
            f"""
<div class="focus-card">
  <div class="tiny">TODAY'S FOCUS</div>
  <h2>{esc(best['Ticker'])} <span class="level {decision.lower()}">{decision}</span></h2>
  <div>{trigger_label} <b>{usd(best['Entry'])}</b> · Stop <b>{usd(best['Stop'])}</b> · Target <b>{usd(best['Target'])}</b></div>
  <div class="muted">{esc(best['Setup'])} · Score {best['Score']}/100 · R/R {best['R/R']}R</div>
  <hr>
  <div class="muted">{esc(decision_line(decision))}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title">Focus Today</div>', unsafe_allow_html=True)
        if actionable.empty:
            st.markdown("<div class='card-compact muted'>No actionable setups today. Best action is to wait.</div>", unsafe_allow_html=True)
        else:
            render_stock_grid(actionable, summary["total_value"], expanded_first=False)

        st.markdown('<div class="section-title">Skip Today</div>', unsafe_allow_html=True)
        if skip.empty:
            st.markdown("<div class='card-compact muted'>No skip list right now.</div>", unsafe_allow_html=True)
        else:
            render_stock_grid(skip, summary["total_value"], expanded_first=False)

with right:
    st.markdown('<div class="section-title">Dashboard</div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.metric("Portfolio", usd(summary["total_value"]))
    k2.metric("P/L", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    k3.metric("Positions", str(summary["positions"]), summary["risk_label"])

    st.markdown('<div class="section-title">Holdings</div>', unsafe_allow_html=True)
    holdings_view(holdings, height=210)

    lower_left, lower_right = st.columns([1, .9], gap="small")
    with lower_left:
        st.markdown('<div class="section-title">Alerts</div>', unsafe_allow_html=True)
        for note in decision_alerts(desk, holdings)[:3]:
            st.markdown(f"<div class='card-compact'>{esc(note)}</div>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Risk Notes</div>', unsafe_allow_html=True)
        for note in top_risk_notes(holdings)[:2]:
            st.markdown(f"<div class='card-compact'>{esc(note)}</div>", unsafe_allow_html=True)
    with lower_right:
        st.markdown('<div class="section-title">Allocation</div>', unsafe_allow_html=True)
        st.plotly_chart(allocation_chart(holdings), use_container_width=True)

    perf = get_last_call_performance(limit=3)
    with st.expander("Decision History", expanded=False):
        if perf.empty:
            st.caption("History starts after the first day of saved desk calls.")
        else:
            for _, r in perf.iterrows():
                st.markdown(
                    f"<div class='card-compact'><b>{esc(r['ticker'])}</b> · {esc(r['decision'])} · {r['return_pct']:+.2f}% since call<br><span class='muted'>Then {usd(r['then_price'])} · Now {usd(r['now_price'])} · {esc(r['snapshot_date'])}</span></div>",
                    unsafe_allow_html=True,
                )

    journal_panel()
    manage_holdings_inline(holdings)
