import streamlit as st
from services.database import init_db, read_table
from services.portfolio import enrich_holdings, portfolio_metrics, rebalance_actions
from services.ai import generate_portfolio_review

st.set_page_config(page_title='AI Review', layout='wide')
init_db()
st.title('AI Review')

new_cash = st.number_input('New cash to deploy (USD)', min_value=0.0, value=0.0, step=100.0)
df = enrich_holdings(read_table('holdings'))
metrics = portfolio_metrics(df)
rb = rebalance_actions(df, new_cash)
top = df.sort_values('market_value', ascending=False).head(5) if not df.empty else df

if st.button('Generate Review'):
    st.markdown(generate_portfolio_review(metrics, top, rb))
else:
    st.info('Click Generate Review. Add OPENAI_API_KEY in Streamlit secrets later for GPT-powered analysis.')
