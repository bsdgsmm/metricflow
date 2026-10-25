import pandas as pd
import pytest

from metricflow_platform.database import connect
from metricflow_platform.metrics import LINE_COLUMNS, summarize_kpis

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def marts(base_settings):
    with connect(base_settings.database) as conn:
        exists = conn.execute("select to_regclass('marts.mart_monthly_kpis')").fetchone()[0]
        if exists is None:
            pytest.skip("dbt marts have not been built; run `metricflow_platform dbt build`")
        lines = pd.DataFrame(
            conn.execute(f"select {', '.join(LINE_COLUMNS)} from marts.fct_order_items").fetchall(),
            columns=LINE_COLUMNS,
        )
        totals = conn.execute(
            """
            select sum(orders), sum(net_sales), sum(net_revenue), sum(gross_profit)
            from marts.mart_monthly_kpis
            """
        ).fetchone()
        repeat = conn.execute(
            """
            select avg(case when order_count >= 2 then 1.0 else 0 end)
            from marts.mart_customer_metrics
            where order_count > 0
            """
        ).fetchone()[0]
    return lines, totals, repeat


def test_python_kpis_match_dbt_marts(marts):
    lines, (orders, net_sales, net_revenue, gross_profit), repeat_rate = marts

    summary = summarize_kpis(lines)

    orders = int(orders)

    assert summary.orders == orders
    assert summary.net_sales == pytest.approx(float(net_sales), abs=0.01)
    assert summary.net_revenue == pytest.approx(float(net_revenue), abs=0.01)
    assert summary.gross_profit == pytest.approx(float(gross_profit), abs=0.01)
    assert summary.average_order_value == pytest.approx(float(net_sales) / orders)
    assert summary.repeat_purchase_rate == pytest.approx(float(repeat_rate))
