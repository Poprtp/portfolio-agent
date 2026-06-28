import streamlit as st
from services.database import init_db

st.set_page_config(page_title='AI Portfolio OS 3.0', page_icon='📈', layout='wide')
init_db()

st.title('AI Portfolio OS 3.0')
st.caption('Personal portfolio dashboard, risk control, watchlist ranking, and AI review.')

st.markdown('''
### Start here
Use the sidebar pages to manage your portfolio.

- **Dashboard**: portfolio value, allocation, risk, and rebalance actions
- **Holdings**: add or edit positions
- **Transactions**: record buy/sell history
- **Watchlist**: rank stocks by price vs fair value and conviction
- **AI Review**: portfolio summary and action plan
- **Price Chart**: check stock price history
- **Settings**: deployment and API key notes
''')

st.info('Go to Dashboard from the sidebar to view your portfolio.')
