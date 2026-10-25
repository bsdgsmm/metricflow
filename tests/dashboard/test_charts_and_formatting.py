import pandas as pd

from metricflow_platform.dashboard import charts, formatting


def monthly(months, years=("2024",)):
    rows = []
    for year in years:
        for month in range(1, months + 1):
            rows.append(
                {
                    "month_start": pd.Timestamp(f"{year}-{month:02d}-01"),
                    "orders": month,
                    "net_revenue": month * 100.0,
                    "average_order_value": 100.0,
                    "gross_margin": 0.4,
                }
            )
    return pd.DataFrame(rows)


def test_monthly_bars_use_single_series_and_axis():
    fig = charts.monthly_bars(monthly(3), "net_revenue", title="Net revenue", y_title="Net revenue")

    assert len(fig.data) == 1
    assert fig.data[0].marker.color == charts.PRIMARY
    assert "yaxis2" not in fig.layout
    assert fig.data[0].hovertemplate


def test_year_lines_keep_fixed_colors_and_last_three_years():
    data = monthly(12, years=("2022", "2023", "2024", "2025"))
    yoy = data.assign(
        year=data["month_start"].dt.year.astype(str),
        month=data["month_start"].dt.month,
        month_label=data["month_start"].dt.strftime("%b"),
    )

    fig = charts.year_over_year_lines(yoy, "net_revenue", title="YoY", y_title="Net revenue")

    assert [trace.name for trace in fig.data] == ["2023", "2024", "2025"]
    assert [trace.line.color for trace in fig.data] == list(charts.CATEGORICAL[:3])
    assert fig.layout.showlegend is True
    assert [a.text for a in fig.layout.annotations] == ["2023", "2024", "2025"]


def test_ranked_bars_put_largest_value_on_top():
    frame = pd.DataFrame({"category": ["A", "B", "C"], "net_revenue": [5.0, 30.0, 10.0]})

    fig = charts.ranked_bars(frame, "category", "net_revenue", title="t", x_title="x")

    assert list(fig.data[0].y) == ["A", "C", "B"]


def test_retention_heatmap_scales_to_months_after_first():
    matrix = pd.DataFrame({0: [1.0, 1.0], 1: [0.2, 0.1], 2: [0.15, 0.05]}, index=["a", "b"])

    fig = charts.retention_heatmap(matrix, title="Retention")

    assert fig.data[0].zmax == 0.2
    assert list(fig.data[0].x) == ["0", "1", "2"]


def test_formatting_handles_missing_values():
    assert formatting.currency(None) == "n/a"
    assert formatting.currency(1234567.891) == "1,234,568"
    assert formatting.currency_precise(12.5) == "12.50"
    assert formatting.percent(0.1234) == "12.3%"
    assert formatting.integer(12000) == "12,000"


def test_change_formatting():
    assert formatting.change(120, 100) == "+20.0%"
    assert formatting.change(90, 100) == "-10.0%"
    assert formatting.change(10, 0) is None
    assert formatting.change(None, 5) is None
    assert formatting.point_change(0.45, 0.40) == "+5.0 pp"
    assert formatting.point_change(0.45, None) is None
