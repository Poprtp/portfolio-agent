from datetime import date

import streamlit as st

from services.database import get_setting, init_db
from services.portfolio import (
    add_transaction,
    delete_holding,
    get_enriched_holdings,
    get_transactions,
    portfolio_summary,
    rebalance_actions,
    refresh_prices,
    upsert_holding,
    upsert_holding_auto,
)
from services.trade import (
    build_trade_plan,
    delete_trade_plan,
    get_trade_journal,
    professional_trade_setup,
    save_trade_plan,
    trade_score,
    update_trade_status,
)
from services.watchlist import (
    delete_watchlist,
    get_top_opportunities,
    get_watchlist,
    refresh_watchlist_prices,
    upsert_watchlist,
)
from utils.charts import allocation_chart
from utils.formatting import pct, usd

st.set_page_config(page_title="AI Portfolio OS", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
init_db()

st.markdown(
    """
<style>
.block-container {padding: .65rem 1.05rem 1rem 1.05rem; max-width: 1160px;}
h1 {font-size: 1.2rem !important; margin: 0 0 .3rem 0 !important; letter-spacing: -0.03em;}
h2 {font-size: .98rem !important; margin: .55rem 0 .25rem 0 !important;}
h3 {font-size: .88rem !important; margin: .45rem 0 .25rem 0 !important;}
[data-testid="stSidebar"] {background: #0f172a; border-right: 1px solid #1f2937; min-width: 210px !important; max-width: 210px !important;}
[data-testid="stSidebar"] .block-container {padding: 1rem .75rem;}
[data-testid="stMetric"] {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:9px 11px;}
[data-testid="stMetricLabel"] {font-size:.72rem; color:#9ca3af;}
[data-testid="stMetricValue"] {font-size:1.0rem;}
.stDataFrame {border:1px solid #1f2937; border-radius:12px; overflow:hidden;}
.action-card {background:#111827; border:1px solid #1f2937; border-radius:12px; padding:9px 11px; margin-bottom:8px;}
.action-card strong {font-size:.86rem;}
.green {color:#22c55e;} .red {color:#ef4444;} .yellow {color:#facc15;} .muted {color:#9ca3af;} .blue {color:#60a5fa;}
hr {border-color:#1f2937; margin:.65rem 0;}
button[kind="secondary"] {border-radius:10px !important;}
</style>
""",
    unsafe_allow_html=True,
)

PAGES = ["Dashboard", "Portfolio", "Transactions", "Watchlist", "Trade Assistant", "Trade Journal", "Settings"]
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
st.caption("Professional trader logic: capital protection first, defined risk, no chasing extended moves.")
nav_cols = st.columns([.85, .85, 1.05, .9, .95, 1.05, .85, 1.2])
for idx, page in enumerate(PAGES):
    with nav_cols[idx]:
        if st.button(page, use_container_width=True, type="primary" if page == nav else "secondary"):
            set_page(page)


def kpi_row():
    c1, c2, c3 = st.columns(3)
    c1.metric("Portfolio", usd(summary["total_value"]))
    c2.metric("Gain / Loss", usd(summary["total_gain_loss"]), pct(summary["total_return_pct"]))
    c3.metric("Risk", summary["risk_label"], f'{summary["risk_score"]}/100')


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


def action_cards(limit=4, source_df=None):
    source = holdings_df if source_df is None else source_df
    actions = rebalance_actions(source)
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


def opportunity_cards(limit=3):
    opp = get_top_opportunities(limit)
    if opp.empty:
        st.info("No watchlist opportunities yet.")
        return
    for _, row in opp.iterrows():
        decision = row.get("decision", "WAIT")
        color = "green" if decision == "ACTIONABLE" else "yellow" if "WATCH" in decision or "READY" in decision else "muted"
        st.markdown(
            f"""
<div class="action-card">
  <strong>{row['ticker']}</strong> <span class="{color}">{decision}</span><br>
  <span class="muted">Trade {row.get('trade_action', '-')} · {row.get('setup_type', '-')} · Tech {int(row.get('technical_score', 0))}/100</span><br>
  <span class="muted">Valuation {row.get('valuation_status', '-')} · MOS {row.get('mos', 0):.1f}%</span>
</div>
""",
            unsafe_allow_html=True,
        )


with st.sidebar:
    st.markdown(f"### {nav}")
    st.caption("Quick actions")
    st.divider()

    if nav == "Dashboard":
        st.metric("Risk", summary["risk_label"], f'{summary["risk_score"]}/100')
        st.caption("Top actions")
        action_cards(limit=2)

    elif nav == "Portfolio":
        st.caption("Add / Edit Holding")
        st.info("Type only the ticker. Name, type, sector, target weight, and latest price are filled automatically.")
        with st.form("holding_form"):
            ticker = st.text_input("Ticker", value="TSM").upper().strip()
            shares = st.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
            avg_cost = st.number_input("Average Cost", min_value=0.0, value=0.0, step=1.0)
            if st.form_submit_button("Save holding", use_container_width=True) and ticker:
                profile = upsert_holding_auto(ticker, shares, avg_cost)
                st.success(f"Saved {ticker}: {profile.get('name', ticker)}")
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

    elif nav == "Trade Assistant":
        st.caption("15-year trader logic")
        st.info("Setup quality and execution feasibility are separated. The system does not execute orders.")
        st.metric("Portfolio", usd(summary["total_value"]))
        st.metric("Cash", usd(summary["cash"]))

    elif nav == "Trade Journal":
        journal = get_trade_journal()
        st.caption("Trade records")
        st.metric("Plans", len(journal))
        if not journal.empty:
            planned_count = int((journal["status"] == "Planned").sum())
            open_count = int((journal["status"] == "Open").sum())
            ready_count = int((journal.get("readiness", "") == "READY").sum()) if "readiness" in journal.columns else 0
            st.metric("Planned", planned_count)
            st.metric("Open", open_count)
            st.metric("Ready", ready_count)

            st.divider()
            trade_id = st.selectbox("Trade ID", journal["id"].tolist())
            new_status = st.selectbox("Update Status", ["Planned", "Open", "Closed", "Cancelled"])
            if st.button("Save status", use_container_width=True):
                update_trade_status(trade_id, new_status)
                st.rerun()
            if st.button("Delete plan", use_container_width=True):
                delete_trade_plan(trade_id)
                st.rerun()

    elif nav == "Settings":
        if st.button("Repair database", use_container_width=True):
            init_db()
            st.success("Database ready")
        st.caption("Streamlit Cloud may reset SQLite after redeploy.")


if nav == "Dashboard":
    top_left, top_right = st.columns([1, .22])
    with top_left:
        st.caption("Compact portfolio dashboard")
        last_sync = get_setting("last_price_sync", "Not synced yet")
        st.caption(f"Last price sync: {last_sync}")
    with top_right:
        if st.button("Refresh", use_container_width=True):
            refresh_prices()
            refresh_watchlist_prices()
            st.rerun()

    kpi_row()

    left, right = st.columns([1.25, 1], gap="medium")
    with left:
        st.subheader("Holdings")
        holdings_table(holdings_df, height=220)
    with right:
        st.subheader("Allocation")
        st.plotly_chart(allocation_chart(holdings_df), use_container_width=True)

    b1, b2 = st.columns([1, 1], gap="medium")
    with b1:
        st.subheader("Actions")
        action_cards()
    with b2:
        st.subheader("Watchlist Opportunities")
        opportunity_cards()

    st.subheader("Recent Transactions")
    recent_transaction_cards(limit=3)

elif nav == "Portfolio":
    st.caption("Manage current holdings")
    holdings_table(holdings_df, height=430, full=True)

elif nav == "Transactions":
    st.caption("Buy, sell, and cash movements")
    st.dataframe(get_transactions(), use_container_width=True, hide_index=True, height=470)

elif nav == "Watchlist":
    st.caption("Unified watchlist: valuation + professional technical setup. Valuation is not a trade signal by itself.")
    wdf = get_watchlist()
    if wdf.empty:
        st.info("No watchlist yet.")
    else:
        show = wdf[[
            "ticker", "name", "current_price", "fair_value", "target_buy_price", "mos",
            "valuation_status", "trade_action", "setup_type", "technical_score", "decision", "score"
        ]].rename(
            columns={
                "ticker": "Ticker",
                "name": "Name",
                "current_price": "Price",
                "fair_value": "Fair Value",
                "target_buy_price": "Buy Zone",
                "mos": "MOS %",
                "valuation_status": "Valuation",
                "trade_action": "Trade Setup",
                "setup_type": "Setup Type",
                "technical_score": "Technical",
                "decision": "Decision",
                "score": "Score",
            }
        )
        st.dataframe(show, use_container_width=True, hide_index=True, height=430)

elif nav == "Trade Assistant":
    st.caption("Professional trade assistant: type a ticker and get Entry / Stop / Target using 15-year trader logic.")

    top_left, top_right = st.columns([1, 1], gap="medium")
    with top_left:
        ticker = st.text_input("Ticker", value="TSM", help="Type only the ticker, e.g. TSM, MSFT, NVDA").upper().strip()
    with top_right:
        st.caption("Uses 1-year price action, trend filter, MA20/50/200, ATR, support/resistance, and disciplined risk rules.")

    setup = professional_trade_setup(ticker)

    left, right = st.columns([1, 1], gap="medium")
    with left:
        st.subheader("Professional Setup")
        entry = st.number_input("Suggested Entry", min_value=0.0, value=float(setup.get("entry", 0)), step=1.0)
        stop = st.number_input("Suggested Stop Loss", min_value=0.0, value=float(setup.get("stop", 0)), step=1.0)
        target = st.number_input("Suggested Target", min_value=0.0, value=float(setup.get("target", 0)), step=1.0)
        st.caption("You can override these levels before saving the plan.")

    with right:
        st.subheader("Risk Settings")
        account_size = st.number_input("Account / Portfolio Size", min_value=0.0, value=float(summary["total_value"] or 10000), step=100.0)
        cash_available = st.number_input("Cash Available", min_value=0.0, value=float(summary["cash"] or 0), step=100.0)
        risk_pct = st.number_input("Risk per Trade %", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
        max_position_pct = st.number_input("Max Position %", min_value=1.0, max_value=100.0, value=15.0, step=1.0)

    plan = build_trade_plan(ticker, entry, stop, target, account_size, cash_available, risk_pct, max_position_pct)
    existing_weight = 0.0
    if not holdings_df.empty and ticker in holdings_df["ticker"].values:
        existing_weight = float(holdings_df.loc[holdings_df["ticker"] == ticker, "weight"].iloc[0])
    analysis = trade_score(plan, current_weight=existing_weight, cash_weight=float(summary.get("cash_weight", 0)), setup=setup)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Setup Quality", f'{analysis["setup_score"]}/100', analysis["setup_recommendation"])
    c2.metric("Execution", analysis["execution_status"], analysis["recommendation"])
    c3.metric("Entry", usd(entry))
    c4.metric("Stop", usd(stop))
    c5.metric("Target / R", f'{usd(target)} · {plan["risk_reward"]:.2f}R')

    st.subheader("Trade Assistant Review")
    st.markdown(
        f"""
<div class="action-card">
  <strong>{ticker}</strong> <span class="{analysis["color"]}">{analysis["recommendation"]}</span><br>
  <span class="muted">{setup.get("setup_type", "Setup")} · Trend {setup.get("trend", "-")} · Momentum {setup.get("momentum", "-")} · Setup {setup.get("confidence", 0)}/100</span><br>
  <span class="muted">Current {usd(setup.get("current_price", 0))} · MA20 {usd(setup.get("ma20", 0))} · MA50 {usd(setup.get("ma50", 0))} · ATR {usd(setup.get("atr", 0))}</span><br>
  <span class="muted">Shares {plan["suggested_shares"]:,} · Capital {usd(plan["capital_needed"])} · Max loss {usd(plan["max_loss"])} · Position {plan["position_pct"]:.1f}%</span><br>
  <span class="muted">Rule: {setup.get("trade_rule", "Respect the stop and avoid forcing trades.")}</span>
</div>
""",
        unsafe_allow_html=True,
    )

    r1, r2 = st.columns([1, 1], gap="medium")
    with r1:
        st.markdown("**Professional Reasons**")
        if analysis["reasons"]:
            for item in analysis["reasons"]:
                st.markdown(f"- {item}")
        else:
            st.caption("No positive factors yet.")
    with r2:
        st.markdown("**Professional Risks**")
        if analysis["risks"]:
            for item in analysis["risks"]:
                st.markdown(f"- {item}")
        else:
            st.caption("No major rule-based risks.")

    with st.form("save_trade_plan_form"):
        thesis_default = f"{setup.get('setup_type', '')} - {analysis.get('summary', '')}; " + ("; ".join(analysis["reasons"]) if analysis["reasons"] else "")
        risk_default = "; ".join(analysis["risks"]) if analysis["risks"] else ""
        thesis = st.text_area("Trade thesis", value=thesis_default.strip("; "), height=70)
        exit_plan = st.text_area("Exit plan", value=f"Entry: {entry}. Stop: {stop}. Target: {target}. Risk/reward: {plan['risk_reward']:.2f}R.", height=70)
        note = st.text_input("Plan note", value=risk_default)
        save_plan = st.form_submit_button("Save to Trade Journal", use_container_width=True)
        if save_plan:
            save_trade_plan(
                ticker,
                entry,
                stop,
                target,
                plan,
                note,
                checklist_score=analysis["score"],
                readiness=analysis["recommendation"],
                thesis=thesis,
                exit_plan=exit_plan,
            )
            st.success("Saved to Trade Journal")

    st.caption("Professional rule-based assistant only. It does not place orders or guarantee returns. Use it as decision support, not a signal service.")

elif nav == "Trade Journal":
    st.caption("Saved trade plans and follow-up status")
    journal = get_trade_journal()
    if journal.empty:
        st.info("No trade plans yet. Create one from Trade Assistant.")
    else:
        show = journal.rename(
            columns={
                "id": "ID",
                "created_at": "Created",
                "ticker": "Ticker",
                "status": "Status",
                "entry": "Entry",
                "stop": "Stop",
                "target": "Target",
                "shares": "Shares",
                "capital_needed": "Capital",
                "max_loss": "Max Loss",
                "max_gain": "Max Gain",
                "risk_reward": "R/R",
                "setup_status": "Setup",
                "checklist_score": "Trade Score",
                "readiness": "Recommendation",
                "thesis": "Thesis",
                "exit_plan": "Exit Plan",
                "note": "Note",
            }
        )
        st.dataframe(show, use_container_width=True, hide_index=True, height=470)

elif nav == "Settings":
    st.caption("Minimal settings")
    st.info("Use Repair database if old cloud database schema causes issues.")
    st.write(f"Last price sync: {get_setting('last_price_sync', 'Not synced yet')}")
    st.write(f"Last watchlist sync: {get_setting('last_watchlist_sync', 'Not synced yet')}")
