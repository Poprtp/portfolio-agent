import streamlit as st
from services.portfolio import get_enriched_holdings, upsert_holding, delete_holding

st.set_page_config(page_title="Holdings", layout="wide")
st.title("Holdings")

df = get_enriched_holdings()
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Add / Edit Holding")
with st.form("holding_form"):
    col1, col2, col3 = st.columns(3)
    ticker = col1.text_input("Ticker", value="TSM").upper().strip()
    name = col2.text_input("Name", value="Taiwan Semiconductor ADR")
    asset_type = col3.selectbox("Asset Type", ["Stock", "ETF", "Cash", "Crypto", "Other"])
    col4, col5, col6 = st.columns(3)
    shares = col4.number_input("Shares", min_value=0.0, value=0.0, step=1.0)
    avg_cost = col5.number_input("Average Cost", min_value=0.0, value=0.0, step=1.0)
    target_weight = col6.number_input("Target Weight %", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
    sector = st.text_input("Sector", value="Semiconductors")
    submitted = st.form_submit_button("Save holding")
    if submitted and ticker:
        upsert_holding(ticker, name, shares, avg_cost, target_weight, asset_type, sector)
        st.success(f"Saved {ticker}")
        st.rerun()

st.subheader("Delete Holding")
if not df.empty:
    del_ticker = st.selectbox("Select ticker to delete", df["ticker"].tolist())
    if st.button("Delete selected holding", type="secondary"):
        delete_holding(del_ticker)
        st.warning(f"Deleted {del_ticker}")
        st.rerun()
