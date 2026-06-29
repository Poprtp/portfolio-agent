import plotly.express as px
import plotly.graph_objects as go


MONO_COLORS = ["#f5f5f5", "#d4d4d4", "#a3a3a3", "#737373", "#525252", "#404040", "#262626"]


def allocation_chart(df):
    if df.empty or "market_value" not in df.columns:
        return go.Figure()
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
