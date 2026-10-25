from __future__ import annotations

from decimal import Decimal

import pandas as pd
import psycopg

ORDER_LINES = """
    select
        items.order_id,
        items.order_date,
        items.is_cancelled,
        items.customer_key,
        products.product_id,
        products.product_name,
        products.category,
        customers.acquisition_channel,
        customers.country,
        items.quantity,
        items.returned_quantity,
        items.gross_revenue,
        items.discount_amount,
        items.net_sales,
        items.refund_amount,
        items.net_revenue,
        items.cost_of_goods_sold,
        items.gross_profit
    from marts.fct_order_items as items
    inner join marts.dim_products as products
        on items.product_key = products.product_key
    inner join marts.dim_customers as customers
        on items.customer_key = customers.customer_key
"""

PRODUCT_PERFORMANCE = """
    select
        product_id,
        product_name,
        category,
        is_active,
        net_revenue,
        net_revenue_recent_6m,
        net_revenue_prior_6m,
        net_revenue_6m_change,
        sales_trend
    from marts.mart_product_performance
"""

CUSTOMER_METRICS = """
    select
        customer_key,
        acquisition_channel,
        country,
        first_order_month,
        order_count,
        frequency_segment,
        lifetime_net_revenue,
        net_revenue_first_365d,
        has_full_first_year
    from marts.mart_customer_metrics
"""

COHORT_RETENTION = """
    select cohort_month, months_since_first_order, cohort_size, retention_rate
    from marts.mart_cohort_retention
"""

DATA_EXTENT = """
    select min(order_date) as first_order_date, max(order_date) as last_order_date
    from marts.fct_orders
"""


def fetch_frame(conn: psycopg.Connection, query: str) -> pd.DataFrame:
    """Run a query and return a DataFrame with numeric columns as floats and dates as datetimes."""
    with conn.cursor() as cur:
        cur.execute(query)
        columns = [column.name for column in cur.description]
        frame = pd.DataFrame(cur.fetchall(), columns=columns)
    for column in frame.columns:
        sample = frame[column].dropna()
        if sample.empty:
            continue
        if isinstance(sample.iloc[0], Decimal):
            frame[column] = frame[column].astype(float)
        elif column.endswith(("_date", "_month")):
            frame[column] = pd.to_datetime(frame[column])
    return frame
