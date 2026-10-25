"""Business metric formulas shared by the dashboard and tests.

The dbt marts are the system of record for metrics. These functions apply the same
definitions to filtered order-line data (for example a date range or a subset of categories)
where pre-aggregated monthly tables cannot be reused, because distinct counts such as orders
and customers are not additive. Definitions are documented in docs/metrics.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

LINE_COLUMNS = (
    "order_id",
    "customer_key",
    "is_cancelled",
    "quantity",
    "gross_revenue",
    "discount_amount",
    "net_sales",
    "refund_amount",
    "net_revenue",
    "cost_of_goods_sold",
    "gross_profit",
)


@dataclass(frozen=True)
class KpiSummary:
    orders: int
    customers: int
    units: int
    gross_revenue: float
    discount_amount: float
    net_sales: float
    refund_amount: float
    net_revenue: float
    gross_profit: float
    average_order_value: float | None
    gross_margin: float | None
    repeat_purchase_rate: float | None


def safe_ratio(numerator: float, denominator: float) -> float | None:
    """Divide, returning None instead of raising or producing infinity for a zero denominator."""
    if denominator == 0 or pd.isna(denominator):
        return None
    return float(numerator) / float(denominator)


def growth(current: float, previous: float | None) -> float | None:
    if previous is None or pd.isna(previous):
        return None
    ratio = safe_ratio(current, previous)
    return None if ratio is None else ratio - 1


def completed_lines(lines: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in LINE_COLUMNS if column not in lines.columns]
    if missing:
        raise ValueError(f"Order-line data is missing columns: {missing}")
    return lines.loc[~lines["is_cancelled"].astype(bool)]


def summarize_kpis(lines: pd.DataFrame) -> KpiSummary:
    """Compute headline KPIs from fct_order_items-shaped rows, excluding cancelled orders."""
    completed = completed_lines(lines)
    amounts = (
        completed[
            [
                "gross_revenue",
                "discount_amount",
                "net_sales",
                "refund_amount",
                "net_revenue",
                "gross_profit",
            ]
        ]
        .astype(float)
        .sum()
    )
    orders = int(completed["order_id"].nunique())
    orders_per_customer = completed.groupby("customer_key")["order_id"].nunique()
    customers = int(orders_per_customer.size)

    return KpiSummary(
        orders=orders,
        customers=customers,
        units=int(completed["quantity"].sum()),
        gross_revenue=round(amounts["gross_revenue"], 2),
        discount_amount=round(amounts["discount_amount"], 2),
        net_sales=round(amounts["net_sales"], 2),
        refund_amount=round(amounts["refund_amount"], 2),
        net_revenue=round(amounts["net_revenue"], 2),
        gross_profit=round(amounts["gross_profit"], 2),
        average_order_value=safe_ratio(amounts["net_sales"], orders),
        gross_margin=safe_ratio(amounts["gross_profit"], amounts["net_revenue"]),
        repeat_purchase_rate=safe_ratio(int((orders_per_customer >= 2).sum()), customers),
    )


def top_share(values: pd.Series, fraction: float) -> float | None:
    """Share of the total held by the top `fraction` of entities, e.g. top 10% of customers."""
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    positive = values.astype(float).clip(lower=0).sort_values(ascending=False)
    if positive.empty or positive.sum() == 0:
        return None
    top_n = max(1, round(len(positive) * fraction))
    return float(positive.iloc[:top_n].sum() / positive.sum())
