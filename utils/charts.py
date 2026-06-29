import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf

try:
    import streamlit as st

    cache_data = st.cache_data(ttl=3600, show_spinner=False)
except Exception:  # pragma: no cover
    def cache_data(func=None, **kwargs):
        def decorator(f):
            return f
        return decorator(func) if func else decorator


MONO_COLORS = ["#f5f5f5", "#d4d4d4", "#a3a3a3", "#737373", "#525252", "#404040", "#262626"]


def empty_chart(message: str = "No chart data yet"):
    fig = go.Figure()
    fig.update_layout(
        height=210,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d4d4d4", size=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(color="#9a9a9a", size=12),
            )
        ],
    )
    return fig


def allocation_chart(df):
    if df.empty or "market_value" not in df.columns:
        return empty_chart("No allocation data yet")
    fig = px.pie(df, values="market_value", names="ticker", hole=0.72, color_discrete_sequence=MONO_COLORS)
    fig.update_traces(textinfo="percent", textfont_size=10, marker=dict(line=dict(color="#050505", width=2)))
    fig.update_layout(
        height=210,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=10, color="#d4d4d4")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


@cache_data
def _close_history(ticker: str, period: str = "3mo") -> pd.Series:
    ticker = str(ticker).upper().strip()
    if not ticker:
        return pd.Series(dtype=float)
    try:
        hist = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        if hist.empty or "Close" not in hist.columns:
            return pd.Series(dtype=float)
        close = hist["Close"].dropna().astype(float)
        close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
        return close
    except Exception:
        return pd.Series(dtype=float)


def pnl_line_chart(df, period: str = "3mo"):
    """Plot portfolio unrealized P/L trend from holding cost basis and historical close prices.

    This replaces the allocation donut with a more useful risk-management view.
    The line is an estimate based on current shares and average cost, not a full cash-flow adjusted performance chart.
    """
    if df.empty or not {"ticker", "shares", "avg_cost"}.issubset(df.columns):
        return empty_chart("No P/L trend data yet")

    total_pnl = None
    used = 0
    for _, row in df.iterrows():
        ticker = str(row.get("ticker", "")).upper().strip()
        try:
            shares = float(row.get("shares", 0) or 0)
            avg_cost = float(row.get("avg_cost", 0) or 0)
        except Exception:
            continue
        if not ticker or shares <= 0 or avg_cost <= 0:
            continue
        close = _close_history(ticker, period)
        if close.empty:
            continue
        pnl = (close - avg_cost) * shares
        pnl.name = ticker
        total_pnl = pnl if total_pnl is None else total_pnl.add(pnl, fill_value=0)
        used += 1

    if total_pnl is None or total_pnl.empty:
        return empty_chart("No historical P/L data available")

    chart_df = total_pnl.sort_index().reset_index()
    chart_df.columns = ["date", "pnl"]
    chart_df["date_label"] = chart_df["date"].dt.strftime("%b %d")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["pnl"],
            mode="lines",
            name="Unrealized P/L",
            line=dict(color="#f5f5f5", width=2),
            hovertemplate="%{x|%b %d}<br>P/L: $%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#737373")
    fig.update_layout(
        height=230,
        margin=dict(l=0, r=0, t=4, b=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d4d4d4", size=10),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#9a9a9a", size=9),
        ),
        yaxis=dict(
            title="",
            showgrid=True,
            gridcolor="#2b2b2b",
            zeroline=False,
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(color="#9a9a9a", size=9),
        ),
    )
    fig.update_xaxes(rangeslider_visible=False)
    return fig
