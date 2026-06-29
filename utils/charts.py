import plotly.express as px
import plotly.graph_objects as go


def allocation_chart(df):
    if df.empty or "market_value" not in df.columns:
        return go.Figure()
    fig = px.pie(df, values="market_value", names="ticker", hole=0.68)
    fig.update_traces(textinfo="percent", textfont_size=10)
    fig.update_layout(
        height=230,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
