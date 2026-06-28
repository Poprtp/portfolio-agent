import streamlit as st
from services.database import init_db, read_table, upsert_holding, delete_holding
from services.portfolio import enrich_holdings

st.set_page_config(page_title='Holdings', layout='wide')
init_db()
st.title('Holdings')

with st.form('holding_form'):
    st.subheader('Add / Update Holding')
    c1, c2, c3 = st.columns(3)
    ticker = c1.text_input('Ticker', value='TSM').upper()
    name = c2.text_input('Name', value='Taiwan Semiconductor ADR')
    target_weight = c3.number_input('Target weight %', min_value=0.0, max_value=100.0, value=20.0)
    c4, c5 = st.columns(2)
    shares = c4.number_input('Shares', min_value=0.0, value=0.0, step=1.0)
    avg_cost = c5.number_input('Average cost', min_value=0.0, value=0.0, step=1.0)
    submitted = st.form_submit_button('Save holding')
    if submitted and ticker and name:
        upsert_holding(ticker, name, shares, avg_cost, target_weight)
        st.success(f'Saved {ticker}')
        st.rerun()

holdings = enrich_holdings(read_table('holdings'))
st.subheader('Current Holdings')
st.dataframe(holdings, use_container_width=True, hide_index=True)

st.subheader('Delete Holding')
selected = st.selectbox('Ticker to delete', holdings['ticker'].tolist() if not holdings.empty else [])
if st.button('Delete selected holding') and selected:
    delete_holding(selected)
    st.warning(f'Deleted {selected}')
    st.rerun()
