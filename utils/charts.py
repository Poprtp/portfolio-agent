import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def allocation_chart(df: pd.DataFrame):
    if df.empty:
        return go.Figure()
    active = df[df["market_value"] > 0].copy()
    if active.empty:
        return go.Figure()
    fig = px.pie(active, values="market_value", names="ticker", hole=0.68)
    fig.update_traces(textinfo="percent", textfont_size=11)
    fig.update_layout(
        height=245,
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
        margin=dict(l=8, r=8, t=10, b=8),
        title=f"{ticker} price",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def placeholder_growth_chart(total_value: float):
    # Simple placeholder until portfolio history is added.
    dates = pd.date_range(end=pd.Timestamp.today(), periods=6, freq="M")
    values = [total_value * x for x in [0.92, 0.95, 0.97, 0.96, 0.99, 1.0]]
    fig = px.line(pd.DataFrame({"Date": dates, "Value": values}), x="Date", y="Value")
    fig.update_traces(line_width=2)
    fig.update_layout(
        height=245,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title=None,
        xaxis_title=None,
    )
    return fig
