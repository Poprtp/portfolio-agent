import streamlit as st
from datetime import date
from services.portfolio import add_transaction, get_transactions

st.set_page_config(page_title="Transactions", layout="wide")
st.title("Transactions")

st.subheader("Record Transaction")
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
    submitted = st.form_submit_button("Save transaction")
    if submitted and ticker:
        add_transaction(tx_date, ticker, action, shares, price, fees, note)
        st.success("Transaction saved and holdings updated.")
        st.rerun()

st.divider()
st.subheader("Transaction History")
st.dataframe(get_transactions(), use_container_width=True, hide_index=True)
