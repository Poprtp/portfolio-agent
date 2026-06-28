import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def allocation_chart(df: pd.DataFrame):
    active = df[df["market_value"] > 0].copy()
    if active.empty:
        return go.Figure()
    fig = px.pie(active, values="market_value", names="ticker", hole=0.66)
    fig.update_traces(textinfo="percent", textfont_size=11)
    fig.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def price_chart(df: pd.DataFrame, ticker: str):
    if df.empty:
        return go.Figure()
    fig = px.line(df, x="Date", y="Close")
    fig.update_layout(
        height=300,
        margin=dict(l=8, r=8, t=20, b=8),
        title=f"{ticker} price",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
