import streamlit as st
from services.portfolio import get_enriched_holdings, upsert_holding, delete_holding

st.set_page_config(page_title="Portfolio", layout="wide")
st.title("Portfolio")

st.caption("Add, edit, or remove current holdings.")
df = get_enriched_holdings()
st.dataframe(df, use_container_width=True, hide_index=True, height=320)

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
    del_ticker = st.selectbox("Ticker", [t for t in df["ticker"].tolist() if t != "CASH"])
    if st.button("Delete", type="secondary"):
        delete_holding(del_ticker)
        st.warning(f"Deleted {del_ticker}")
        st.rerun()
