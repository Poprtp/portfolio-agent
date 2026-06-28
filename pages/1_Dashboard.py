import streamlit as st
import plotly.express as px
from services.database import init_db, read_table
from services.portfolio import enrich_holdings, portfolio_metrics, rebalance_actions

st.set_page_config(page_title='Dashboard', layout='wide')
init_db()

st.title('Dashboard')
new_cash = st.sidebar.number_input('New cash to deploy (USD)', min_value=0.0, value=0.0, step=100.0)

holdings = read_table('holdings')
df = enrich_holdings(holdings)
metrics = portfolio_metrics(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric('Portfolio Value', f"${metrics['value']:,.2f}")
c2.metric('Total Gain/Loss', f"${metrics['gain_loss']:,.2f}")
c3.metric('Risk Score', f"{metrics['risk_score']}/100")
c4.metric('Positions', metrics['positions'])

st.subheader('Allocation')
left, right = st.columns([1.25, 1])
with left:
    st.dataframe(df, use_container_width=True, hide_index=True)
with right:
    chart_df = df[df['market_value'] > 0]
    if not chart_df.empty:
        fig = px.pie(chart_df, names='ticker', values='market_value', hole=0.55)
        st.plotly_chart(fig, use_container_width=True)

st.subheader('Rebalance Plan')
rb = rebalance_actions(df, new_cash)
st.dataframe(rb, use_container_width=True, hide_index=True)
