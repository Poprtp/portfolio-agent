import streamlit as st
import plotly.express as px
from services.market import get_history

st.set_page_config(page_title='Price Chart', layout='wide')
st.title('Price Chart')

c1, c2 = st.columns(2)
ticker = c1.text_input('Ticker', value='TSM').upper()
period = c2.selectbox('Period', ['1mo','3mo','6mo','1y','2y','5y'], index=3)

hist = get_history(ticker, period)
if hist.empty:
    st.warning('No price history found.')
else:
    fig = px.line(hist, x='Date', y='Close', title=f'{ticker} price history')
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(hist.tail(20), use_container_width=True, hide_index=True)
