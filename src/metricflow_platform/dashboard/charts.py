"""Plotly figure builders with a consistent, accessible visual language.

Colors come from a validated categorical palette and are assigned by entity in a fixed order.
Single-series charts use one hue and rely on axis labels for identity; every figure keeps a
single y-axis and ships hover tooltips.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

CATEGORICAL = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300")
PRIMARY = CATEGORICAL[0]
SEQUENTIAL = ("#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b")
GRID = "rgba(137, 135, 129, 0.25)"
MUTED_INK = "#898781"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

CURRENCY = ",.0f"


def _base_layout(fig: go.Figure, *, title: str, y_title: str, y_format: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 16}},
        font={"family": FONT, "size": 13},
        margin={"l": 8, "r": 8, "t": 48, "b": 8},
        hovermode="closest",
        barcornerradius=4,
        bargap=0.3,
        showlegend=False,
        height=340,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="", title=None)
    fig.update_yaxes(
        title={"text": y_title, "font": {"color": MUTED_INK}},
        gridcolor=GRID,
        zeroline=True,
        zerolinecolor=GRID,
        tickformat=y_format,
        rangemode="tozero",
    )
    return fig


def monthly_bars(
    monthly: pd.DataFrame, value: str, *, title: str, y_title: str, y_format: str = CURRENCY
) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=monthly["month_start"],
            y=monthly[value],
            marker={"color": PRIMARY},
            hovertemplate=f"%{{x|%b %Y}}<br>{y_title}: %{{y:{y_format}}}<extra></extra>",
        )
    )
    return _base_layout(fig, title=title, y_title=y_title, y_format=y_format)


def monthly_line(
    monthly: pd.DataFrame, value: str, *, title: str, y_title: str, y_format: str = CURRENCY
) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=monthly["month_start"],
            y=monthly[value],
            mode="lines+markers",
            line={"color": PRIMARY, "width": 2},
            marker={"size": 8, "color": PRIMARY},
            hovertemplate=f"%{{x|%b %Y}}<br>{y_title}: %{{y:{y_format}}}<extra></extra>",
        )
    )
    fig.update_layout(hovermode="x unified")
    return _base_layout(fig, title=title, y_title=y_title, y_format=y_format)


def year_over_year_lines(yoy: pd.DataFrame, value: str, *, title: str, y_title: str) -> go.Figure:
    """One line per calendar year over months, colored by year in fixed palette order.

    Only the latest three years are drawn: the palette's first three slots are the largest set
    that stays distinguishable for every pair, including under color-vision deficiencies.
    """
    fig = go.Figure()
    years = sorted(yoy["year"].unique())[-3:]
    for index, year in enumerate(years):
        series = yoy.loc[yoy["year"] == year]
        color = CATEGORICAL[index]
        fig.add_trace(
            go.Scatter(
                x=series["month"],
                y=series[value],
                name=year,
                mode="lines+markers",
                line={"color": color, "width": 2},
                marker={"size": 8, "color": color},
                customdata=series["month_label"],
                hovertemplate=f"{year} %{{customdata}}: %{{y:{CURRENCY}}}<extra></extra>",
            )
        )
        last = series.iloc[-1]
        fig.add_annotation(
            x=last["month"],
            y=last[value],
            text=year,
            showarrow=False,
            xanchor="left",
            xshift=8,
            font={"color": MUTED_INK},
        )
    _base_layout(fig, title=title, y_title=y_title, y_format=CURRENCY)
    fig.update_layout(showlegend=True, legend={"orientation": "h", "y": -0.15}, hovermode="x")
    fig.update_xaxes(
        tickmode="array",
        tickvals=list(range(1, 13)),
        ticktext=[
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        range=[0.5, 12.9],
    )
    return fig


def ranked_bars(
    frame: pd.DataFrame,
    label: str,
    value: str,
    *,
    title: str,
    x_title: str,
    x_format: str = CURRENCY,
) -> go.Figure:
    """Horizontal bars sorted with the largest value on top."""
    ordered = frame.sort_values(value)
    fig = go.Figure(
        go.Bar(
            x=ordered[value],
            y=ordered[label],
            orientation="h",
            marker={"color": PRIMARY},
            text=[format(v, x_format) for v in ordered[value]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"%{{y}}<br>{x_title}: %{{x:{x_format}}}<extra></extra>",
        )
    )
    _base_layout(fig, title=title, y_title="", y_format="")
    largest = float(ordered[value].max()) if len(ordered) else 0.0
    fig.update_xaxes(
        # Headroom so the outside value labels are not clipped at the plot edge.
        range=[0, largest * 1.18 if largest > 0 else 1],
        showgrid=True,
        gridcolor=GRID,
        tickformat=x_format,
        title={"text": x_title},
        rangemode="tozero",
    )
    fig.update_yaxes(showgrid=False, tickformat=None, title=None)
    return fig


def retention_heatmap(matrix: pd.DataFrame, *, title: str) -> go.Figure:
    scale = [[i / (len(SEQUENTIAL) - 1), color] for i, color in enumerate(SEQUENTIAL)]
    fig = go.Figure(
        go.Heatmap(
            z=matrix.to_numpy(),
            x=[str(c) for c in matrix.columns],
            y=list(matrix.index),
            colorscale=scale,
            zmin=0,
            # Month 0 is 100% by definition; scaling to later months keeps their contrast.
            zmax=float(matrix.drop(columns=0, errors="ignore").max().max()),
            xgap=2,
            ygap=2,
            colorbar={"title": "Retention", "tickformat": ".0%"},
            hovertemplate="Cohort %{y}, month %{x}: %{z:.1%}<extra></extra>",
        )
    )
    _base_layout(fig, title=title, y_title="First-order cohort", y_format="")
    fig.update_layout(height=520)
    fig.update_xaxes(title={"text": "Months since first order"}, type="category")
    fig.update_yaxes(autorange="reversed", rangemode=None, type="category", gridcolor=None)
    return fig
