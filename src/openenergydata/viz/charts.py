"""Chart visualization components using Plotly.

Creates interactive charts for energy data visualization.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


# Default technology colors for charts
DEFAULT_TECH_COLORS: Dict[str, str] = {
    "Hydro": "#1f77b4",
    "Solar": "#ff7f0e",
    "Wind": "#2ca02c",
    "Thermal": "#d62728",
    "Gas": "#9467bd",
    "Coal": "#8c564b",
    "Oil": "#e377c2",
    "Nuclear": "#7f7f7f",
    "Geothermal": "#bcbd22",
    "Biomass": "#17becf",
    "Unknown": "#aaaaaa",
}


def generation_mix_chart(
    df: pd.DataFrame,
    chart_type: str = "pie",
    status_filter: str = "Operating",
    tech_colors: Optional[Dict[str, str]] = None,
    title: str = "Generation Mix by Technology",
) -> "go.Figure":
    """Create a generation mix chart by technology.

    Args:
        df: DataFrame with technology and capacity_mw columns
        chart_type: 'pie' or 'bar'
        status_filter: Status to filter by (or 'all')
        tech_colors: Custom color mapping
        title: Chart title

    Returns:
        Plotly Figure object
    """
    if not HAS_PLOTLY:
        raise ImportError("Plotly is required. Install with: pip install plotly")

    tech_colors = tech_colors or DEFAULT_TECH_COLORS

    df_work = df.copy()

    # Filter by status if requested
    if status_filter != "all" and "status" in df_work.columns:
        # Normalize status for comparison
        df_work["status_norm"] = df_work["status"].str.lower()
        df_work = df_work[df_work["status_norm"].str.contains(status_filter.lower(), na=False)]

    if df_work.empty:
        # Return empty figure
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    # Aggregate by technology
    summary = (
        df_work.groupby("technology", dropna=False)
        .agg(total_capacity=("capacity_mw", "sum"))
        .reset_index()
        .sort_values("total_capacity", ascending=False)
    )

    # Create color list
    colors = [tech_colors.get(tech, "#aaaaaa") for tech in summary["technology"]]

    if chart_type == "pie":
        fig = px.pie(
            summary,
            values="total_capacity",
            names="technology",
            title=title,
            color="technology",
            color_discrete_map=tech_colors,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
    else:  # bar
        fig = px.bar(
            summary,
            x="technology",
            y="total_capacity",
            title=title,
            color="technology",
            color_discrete_map=tech_colors,
            labels={"total_capacity": "Capacity (MW)", "technology": "Technology"},
        )
        fig.update_layout(showlegend=False)

    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def load_profile_chart(
    df: pd.DataFrame,
    zone: Optional[str] = None,
    time_range: str = "week",
    title: str = "Load Profile",
) -> "go.Figure":
    """Create a load profile time series chart.

    Args:
        df: DataFrame with zone, month, day, hour, value columns
        zone: Zone to display (uses first zone if None)
        time_range: 'day', 'week', 'month', or 'year'
        title: Chart title

    Returns:
        Plotly Figure object
    """
    if not HAS_PLOTLY:
        raise ImportError("Plotly is required. Install with: pip install plotly")

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    df_work = df.copy()

    # Filter by zone
    if zone:
        df_work = df_work[df_work["zone"] == zone]
    elif "zone" in df_work.columns:
        zone = df_work["zone"].iloc[0]
        df_work = df_work[df_work["zone"] == zone]

    # Detect value column
    value_col = "value"
    for col in ["value", "load_mw", "capacity_factor"]:
        if col in df_work.columns:
            value_col = col
            break

    # Limit data based on time_range
    if time_range == "day":
        df_work = df_work[(df_work["month"] == 1) & (df_work["day"] == 1)]
    elif time_range == "week":
        df_work = df_work[(df_work["month"] == 1) & (df_work["day"] <= 7)]
    elif time_range == "month":
        df_work = df_work[df_work["month"] == 1]

    # Create hour index
    df_work = df_work.sort_values(["month", "day", "hour"])
    df_work["hour_index"] = range(len(df_work))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_work["hour_index"],
        y=df_work[value_col],
        mode="lines",
        name=zone or "Load",
        fill="tozeroy",
        fillcolor="rgba(31, 119, 180, 0.3)",
        line=dict(color="#1f77b4", width=1),
    ))

    # Format x-axis
    if time_range == "day":
        x_title = "Hour"
        tick_vals = list(range(0, 24, 4))
        tick_text = [f"{h}:00" for h in tick_vals]
    elif time_range == "week":
        x_title = "Hour"
        tick_vals = list(range(0, 168, 24))
        tick_text = [f"Day {i+1}" for i in range(7)]
    else:
        x_title = "Hour of Period"
        tick_vals = None
        tick_text = None

    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="Normalized Load" if value_col == "value" else value_col.replace("_", " ").title(),
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified",
    )

    if tick_vals:
        fig.update_xaxes(tickvals=tick_vals, ticktext=tick_text)

    return fig


def capacity_factor_chart(
    df: pd.DataFrame,
    zone: Optional[str] = None,
    technologies: Optional[List[str]] = None,
    time_range: str = "week",
    title: str = "Capacity Factor Profiles",
) -> "go.Figure":
    """Create a capacity factor time series chart for renewable technologies.

    Args:
        df: DataFrame with zone, month, day, hour, capacity_factor columns
        zone: Zone to display
        technologies: List of technologies to include
        time_range: 'day', 'week', 'month', or 'year'
        title: Chart title

    Returns:
        Plotly Figure object
    """
    if not HAS_PLOTLY:
        raise ImportError("Plotly is required. Install with: pip install plotly")

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    df_work = df.copy()

    # Filter by zone
    if zone and "zone" in df_work.columns:
        df_work = df_work[df_work["zone"] == zone]

    # Detect value column
    value_col = "capacity_factor"
    for col in ["capacity_factor", "value", "cf"]:
        if col in df_work.columns:
            value_col = col
            break

    # Limit data based on time_range
    if time_range == "day":
        df_work = df_work[(df_work["month"] == 1) & (df_work["day"] == 1)]
    elif time_range == "week":
        df_work = df_work[(df_work["month"] == 1) & (df_work["day"] <= 7)]
    elif time_range == "month":
        df_work = df_work[df_work["month"] == 1]

    df_work = df_work.sort_values(["month", "day", "hour"])
    df_work["hour_index"] = range(len(df_work))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_work["hour_index"],
        y=df_work[value_col],
        mode="lines",
        name="Capacity Factor",
        line=dict(color="#ff7f0e", width=1),
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Hour",
        yaxis_title="Capacity Factor",
        yaxis_range=[0, 1],
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified",
    )

    return fig


def representative_days_chart(
    df: pd.DataFrame,
    weights_df: pd.DataFrame,
    title: str = "Representative Days",
) -> "go.Figure":
    """Create a chart showing representative day profiles with weights.

    Args:
        df: DataFrame with rep_day, hour, value columns
        weights_df: DataFrame with rep_day, weight columns
        title: Chart title

    Returns:
        Plotly Figure object
    """
    if not HAS_PLOTLY:
        raise ImportError("Plotly is required. Install with: pip install plotly")

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    fig = go.Figure()

    # Detect value column
    value_col = "value"
    for col in ["value", "load", "capacity_factor"]:
        if col in df.columns:
            value_col = col
            break

    # Plot each representative day
    rep_days = sorted(df["rep_day"].unique())
    colors = px.colors.qualitative.Set2

    for i, rep_day in enumerate(rep_days):
        day_data = df[df["rep_day"] == rep_day].sort_values("hour")
        weight = weights_df[weights_df["rep_day"] == rep_day]["weight"].iloc[0] if not weights_df.empty else 1

        fig.add_trace(go.Scatter(
            x=day_data["hour"],
            y=day_data[value_col],
            mode="lines",
            name=f"Day {rep_day} (w={weight:.1f})",
            line=dict(color=colors[i % len(colors)], width=2),
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Hour",
        yaxis_title="Value",
        xaxis=dict(tickmode="linear", tick0=0, dtick=4),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig
