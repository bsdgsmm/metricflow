from decimal import Decimal

import pandas as pd
import pytest

from metricflow_platform.metrics import growth, safe_ratio, summarize_kpis, top_share


def line(order_id, customer, net_sales, *, cancelled=False, refund=0.0, cost=0.0, quantity=1):
    discount = 1.0
    return {
        "order_id": order_id,
        "customer_key": customer,
        "is_cancelled": cancelled,
        "quantity": quantity,
        "gross_revenue": net_sales + discount,
        "discount_amount": discount,
        "net_sales": net_sales,
        "refund_amount": refund,
        "net_revenue": net_sales - refund,
        "cost_of_goods_sold": cost,
        "gross_profit": net_sales - refund - cost,
    }


@pytest.fixture
def lines():
    return pd.DataFrame(
        [
            line("O1", "A", 100.0, cost=40.0),
            line("O1", "A", 50.0, cost=20.0, quantity=2),
            line("O2", "A", 30.0, refund=10.0, cost=12.0),
            line("O3", "B", 20.0, cost=8.0),
            line("O4", "C", 500.0, cancelled=True, cost=100.0),
        ]
    )


def test_summary_excludes_cancelled_orders(lines):
    summary = summarize_kpis(lines)

    assert summary.orders == 3
    assert summary.customers == 2
    assert summary.units == 5
    assert summary.net_sales == 200.0
    assert summary.gross_revenue == 204.0
    assert summary.refund_amount == 10.0
    assert summary.net_revenue == 190.0
    assert summary.gross_profit == 110.0


def test_ratios_use_documented_formulas(lines):
    summary = summarize_kpis(lines)

    assert summary.average_order_value == pytest.approx(200.0 / 3)
    assert summary.gross_margin == pytest.approx(110.0 / 190.0)
    assert summary.repeat_purchase_rate == pytest.approx(0.5)


def test_multiple_lines_of_one_order_do_not_count_as_repeat_purchase():
    summary = summarize_kpis(pd.DataFrame([line("O1", "A", 10.0), line("O1", "A", 5.0)]))

    assert summary.orders == 1
    assert summary.repeat_purchase_rate == 0.0


def test_empty_input_produces_null_ratios(lines):
    summary = summarize_kpis(lines.iloc[0:0])

    assert summary.orders == 0
    assert summary.net_revenue == 0
    assert summary.average_order_value is None
    assert summary.gross_margin is None
    assert summary.repeat_purchase_rate is None


def test_decimal_amounts_from_postgres_are_supported(lines):
    as_decimals = lines.assign(net_sales=lines["net_sales"].map(lambda v: Decimal(str(v))))

    assert summarize_kpis(as_decimals).net_sales == 200.0


def test_missing_columns_raise_clear_error(lines):
    with pytest.raises(ValueError, match="net_revenue"):
        summarize_kpis(lines.drop(columns=["net_revenue"]))


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [(10, 4, 2.5), (0, 5, 0.0), (5, 0, None), (5, float("nan"), None)],
)
def test_safe_ratio(numerator, denominator, expected):
    assert safe_ratio(numerator, denominator) == expected


def test_growth():
    assert growth(120, 100) == pytest.approx(0.2)
    assert growth(80, 100) == pytest.approx(-0.2)
    assert growth(10, 0) is None
    assert growth(10, None) is None


def test_top_share():
    values = pd.Series([50, 20, 10, 10, 5, 5, 0, 0, 0, 0])

    assert top_share(values, 0.1) == pytest.approx(0.5)
    assert top_share(values, 0.2) == pytest.approx(0.7)
    assert top_share(values, 1.0) == pytest.approx(1.0)
    assert top_share(pd.Series([], dtype=float), 0.2) is None
    with pytest.raises(ValueError):
        top_share(values, 0)
