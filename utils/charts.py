import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def allocation_chart(df: pd.DataFrame):
    active = df[df["market_value"] > 0].copy()
    if active.empty:
        return go.Figure()
    fig = px.pie(active, values="market_value", names="ticker", hole=0.55)
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
    return fig


def bar_allocation(df: pd.DataFrame):
    active = df[df["market_value"] > 0].copy().sort_values("weight", ascending=True)
    if active.empty:
        return go.Figure()
    fig = px.bar(active, x="weight", y="ticker", orientation="h", text="weight")
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Weight %", yaxis_title="")
    return fig


def price_chart(df: pd.DataFrame, ticker: str):
    if df.empty:
        return go.Figure()
    fig = px.line(df, x="Date", y="Close", title=f"{ticker} price history")
    fig.update_layout(height=480, margin=dict(l=20, r=20, t=50, b=20))
    return fig
