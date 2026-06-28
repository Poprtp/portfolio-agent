import streamlit as st
from datetime import date
from services.database import init_db, read_table, add_transaction

st.set_page_config(page_title='Transactions', layout='wide')
init_db()
st.title('Transactions')

with st.form('tx_form'):
    c1, c2, c3 = st.columns(3)
    tx_date = c1.date_input('Date', value=date.today())
    ticker = c2.text_input('Ticker', value='QQQI').upper()
    side = c3.selectbox('Side', ['BUY', 'SELL', 'DIVIDEND'])
    c4, c5 = st.columns(2)
    shares = c4.number_input('Shares', min_value=0.0, value=0.0, step=1.0)
    price = c5.number_input('Price', min_value=0.0, value=0.0, step=1.0)
    notes = st.text_input('Notes', value='')
    if st.form_submit_button('Add transaction'):
        add_transaction(str(tx_date), ticker, side, shares, price, notes)
        st.success('Transaction added')
        st.rerun()

st.subheader('History')
st.dataframe(read_table('transactions'), use_container_width=True, hide_index=True)
