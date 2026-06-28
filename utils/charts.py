import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def allocation_chart(df: pd.DataFrame):
    active = df[df["market_value"] > 0].copy()
    if active.empty:
        return go.Figure()
    fig = px.pie(active, values="market_value", names="ticker", hole=0.62)
    fig.update_traces(textinfo="percent", textfont_size=12)
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=8, b=8), legend=dict(orientation="v"))
    return fig


def price_chart(df: pd.DataFrame, ticker: str):
    if df.empty:
        return go.Figure()
    fig = px.line(df, x="Date", y="Close")
    fig.update_layout(height=360, margin=dict(l=8, r=8, t=20, b=8), title=f"{ticker} price")
    return fig
