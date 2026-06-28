import streamlit as st
from services.database import init_db, seed_default_data

st.set_page_config(page_title="AI Portfolio OS 3.1", page_icon="📈", layout="wide")
init_db()
seed_default_data()

st.title("AI Portfolio OS 3.1")
st.caption("Portfolio engine, holdings, transactions, risk control, and watchlist.")

st.markdown("""
### Start here
Use the sidebar pages to manage your portfolio.

- **Dashboard**: portfolio value, allocation, risk, and rebalance actions
- **Holdings**: view and edit current positions
- **Transactions**: record buy/sell transactions and update holdings
- **Watchlist**: rank stocks by target price and conviction
- **AI Review**: rule-based portfolio action plan
- **Price Chart**: stock price history
- **Settings**: database and deployment notes
""")

st.info("Go to Dashboard from the sidebar to view your portfolio.")
