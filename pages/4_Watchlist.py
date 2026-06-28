import streamlit as st
from services.database import init_db, read_table, upsert_watchlist
from services.market import get_prices

st.set_page_config(page_title='Watchlist', layout='wide')
init_db()
st.title('Watchlist')

watch = read_table('watchlist')
if not watch.empty:
    prices = get_prices(watch['ticker'].tolist())
    watch['current_price'] = watch['ticker'].map(prices)
    watch['discount_to_fair_value_pct'] = ((watch['fair_value'] - watch['current_price']) / watch['current_price'] * 100).round(2)
    watch['buy_zone_gap_pct'] = ((watch['target_buy_price'] - watch['current_price']) / watch['current_price'] * 100).round(2)
    watch['score'] = (watch['conviction'] + watch['discount_to_fair_value_pct'].clip(-30, 30)).round(0)
    watch = watch.sort_values('score', ascending=False)
    st.dataframe(watch, use_container_width=True, hide_index=True)

with st.form('watch_form'):
    st.subheader('Add / Update Watchlist')
    c1, c2, c3 = st.columns(3)
    ticker = c1.text_input('Ticker', value='TSM').upper()
    name = c2.text_input('Name', value='Taiwan Semiconductor ADR')
    conviction = c3.slider('Conviction', 0, 100, 80)
    c4, c5 = st.columns(2)
    fair_value = c4.number_input('Fair value', min_value=0.0, value=370.0)
    target_buy = c5.number_input('Target buy price', min_value=0.0, value=390.0)
    notes = st.text_area('Notes', value='')
    if st.form_submit_button('Save watchlist item'):
        upsert_watchlist(ticker, name, fair_value, target_buy, conviction, notes)
        st.success(f'Saved {ticker}')
        st.rerun()
