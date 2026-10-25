from datetime import date

import pandas as pd
import pytest

from metricflow_platform.dashboard import analysis


def line(order_id, customer, order_date, category, net_revenue, *, cancelled=False, **extra):
    return {
        "order_id": order_id,
        "customer_key": customer,
        "order_date": pd.Timestamp(order_date),
        "is_cancelled": cancelled,
        "product_id": extra.get("product_id", f"P-{category}"),
        "product_name": extra.get("product_name", f"{category} item"),
        "category": category,
        "acquisition_channel": extra.get("channel", "email"),
        "country": extra.get("country", "Germany"),
        "quantity": extra.get("quantity", 1),
        "returned_quantity": extra.get("returned", 0),
        "gross_revenue": net_revenue,
        "discount_amount": 0.0,
        "net_sales": net_revenue,
        "refund_amount": 0.0,
        "net_revenue": net_revenue,
        "cost_of_goods_sold": net_revenue / 2,
        "gross_profit": net_revenue / 2,
    }


@pytest.fixture
def lines():
    return pd.DataFrame(
        [
            line("O1", "A", "2024-01-10", "Books", 20.0, channel="email"),
            line("O1", "A", "2024-01-10", "Beauty", 30.0, channel="email"),
            line("O2", "A", "2024-02-03", "Books", 10.0, channel="email", returned=1),
            line("O3", "B", "2024-02-20", "Beauty", 40.0, channel="paid_social"),
            line("O4", "C", "2025-01-05", "Books", 60.0, channel="paid_social"),
            line("O5", "D", "2025-01-06", "Books", 999.0, channel="email", cancelled=True),
        ]
    )


def test_filter_lines_is_inclusive_and_filters_categories(lines):
    filtered = analysis.filter_lines(lines, date(2024, 1, 10), date(2024, 2, 3), ["Books"])

    assert list(filtered["order_id"]) == ["O1", "O2"]


def test_filter_without_categories_keeps_all(lines):
    assert len(analysis.filter_lines(lines, date(2024, 1, 1), date(2025, 12, 31), [])) == 6


def test_previous_period_has_equal_length():
    assert analysis.previous_period(date(2025, 1, 1), date(2025, 12, 31)) == (
        date(2024, 1, 2),
        date(2024, 12, 31),
    )
    assert analysis.previous_period(date(2024, 3, 1), date(2024, 3, 1)) == (
        date(2024, 2, 29),
        date(2024, 2, 29),
    )


def test_monthly_trend_excludes_cancelled_and_computes_ratios(lines):
    monthly = analysis.monthly_trend(lines)

    january_2025 = monthly.loc[monthly["month_start"] == pd.Timestamp("2025-01-01")].iloc[0]
    assert january_2025["orders"] == 1
    assert january_2025["net_revenue"] == 60.0
    january_2024 = monthly.loc[monthly["month_start"] == pd.Timestamp("2024-01-01")].iloc[0]
    assert january_2024["average_order_value"] == 50.0
    assert january_2024["gross_margin"] == 0.5


def test_year_over_year_aligns_months(lines):
    yoy = analysis.year_over_year(analysis.monthly_trend(lines))

    assert set(yoy["year"]) == {"2024", "2025"}
    assert yoy.loc[yoy["year"] == "2025", "month"].tolist() == [1]


def test_category_summary_shares_and_rates(lines):
    summary = analysis.category_summary(lines).set_index("category")

    assert summary.loc["Books", "net_revenue"] == 90.0
    assert summary.loc["Books", "orders"] == 3
    assert summary.loc["Books", "return_rate"] == pytest.approx(1 / 3)
    assert summary["share_of_net_revenue"].sum() == pytest.approx(1.0)
    assert list(summary.index) == ["Books", "Beauty"]


def test_top_products_orders_by_revenue_and_limits(lines):
    top = analysis.top_products(lines, limit=1)

    assert top.loc[0, "product_id"] == "P-Books"
    assert len(top) == 1


def test_repeat_rate_by_segment(lines):
    by_channel = analysis.repeat_rate_by(lines, "acquisition_channel").set_index(
        "acquisition_channel"
    )

    assert by_channel.loc["email", "customers"] == 1
    assert by_channel.loc["email", "repeat_purchase_rate"] == 1.0
    assert by_channel.loc["paid_social", "repeat_purchase_rate"] == 0.0
    assert by_channel.loc["paid_social", "net_revenue_per_customer"] == 50.0


def test_retention_matrix_pivots_and_caps_offsets():
    cohorts = pd.DataFrame(
        {
            "cohort_month": pd.to_datetime(["2024-01-01"] * 3 + ["2024-02-01"] * 2),
            "months_since_first_order": [0, 1, 13, 0, 1],
            "cohort_size": [10, 10, 10, 5, 5],
            "retention_rate": [1.0, 0.2, 0.1, 1.0, 0.4],
        }
    )

    matrix = analysis.retention_matrix(cohorts, max_offset=12)

    assert list(matrix.index) == ["2024-01", "2024-02"]
    assert list(matrix.columns) == [0, 1]
    assert matrix.loc["2024-02", 1] == 0.4
