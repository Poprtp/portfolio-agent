import streamlit as st
from services.watchlist import get_watchlist, upsert_watchlist, delete_watchlist

st.set_page_config(page_title="Watchlist", layout="wide")
st.title("Watchlist")

df = get_watchlist()
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Add / Edit Watchlist")
with st.form("watch_form"):
    c1, c2, c3 = st.columns(3)
    ticker = c1.text_input("Ticker", value="TSM").upper().strip()
    name = c2.text_input("Name", value="Taiwan Semiconductor ADR")
    conviction = c3.slider("Conviction", min_value=1, max_value=5, value=4)
    c4, c5 = st.columns(2)
    fair_value = c4.number_input("Fair Value", min_value=0.0, value=370.0, step=1.0)
    target_buy = c5.number_input("Target Buy Price", min_value=0.0, value=390.0, step=1.0)
    note = st.text_area("Note", value="")
    submitted = st.form_submit_button("Save watchlist item")
    if submitted and ticker:
        upsert_watchlist(ticker, name, fair_value, target_buy, conviction, note)
        st.success(f"Saved {ticker}")
        st.rerun()

if not df.empty:
    st.subheader("Delete Watchlist Item")
    del_ticker = st.selectbox("Ticker", df["ticker"].tolist())
    if st.button("Delete selected item"):
        delete_watchlist(del_ticker)
        st.warning(f"Deleted {del_ticker}")
        st.rerun()
