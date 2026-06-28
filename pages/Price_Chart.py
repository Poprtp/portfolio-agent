import streamlit as st
from services.market import get_price_history
from utils.charts import price_chart

st.set_page_config(page_title="Price Chart", layout="wide")
st.title("Price Chart")

ticker = st.text_input("Ticker", value="TSM").upper().strip()
period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
if ticker:
    df = get_price_history(ticker, period)
    if df.empty:
        st.warning("No price data available.")
    else:
        st.plotly_chart(price_chart(df, ticker), use_container_width=True)
        st.dataframe(df.tail(20), use_container_width=True, hide_index=True)
