"""Pure pandas transformations behind the dashboard views.

Every function takes order-line rows shaped like the ORDER_LINES query and applies the metric
definitions from metricflow_platform.metrics, so filtered views stay consistent with the marts.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

import pandas as pd

from metricflow_platform.metrics import completed_lines, safe_ratio


def filter_lines(
    lines: pd.DataFrame, start: date, end: date, categories: Sequence[str] | None = None
) -> pd.DataFrame:
    """Keep completed-sale lines ordered between start and end (inclusive) in the categories."""
    order_dates = pd.to_datetime(lines["order_date"]).dt.date
    mask = (order_dates >= start) & (order_dates <= end)
    if categories:
        mask &= lines["category"].isin(categories)
    return lines.loc[mask]


def previous_period(start: date, end: date) -> tuple[date, date]:
    """The window of equal length ending the day before `start`."""
    length = end - start
    previous_end = start - timedelta(days=1)
    return previous_end - length, previous_end


def monthly_trend(lines: pd.DataFrame) -> pd.DataFrame:
    completed = completed_lines(lines).assign(
        month_start=lambda df: pd.to_datetime(df["order_date"]).dt.to_period("M").dt.to_timestamp()
    )
    monthly = (
        completed.groupby("month_start")
        .agg(
            orders=("order_id", "nunique"),
            net_sales=("net_sales", "sum"),
            net_revenue=("net_revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
        .reset_index()
    )
    monthly["average_order_value"] = [
        safe_ratio(sales, orders)
        for sales, orders in zip(monthly["net_sales"], monthly["orders"], strict=True)
    ]
    monthly["gross_margin"] = [
        safe_ratio(profit, revenue)
        for profit, revenue in zip(monthly["gross_profit"], monthly["net_revenue"], strict=True)
    ]
    return monthly


def year_over_year(monthly: pd.DataFrame) -> pd.DataFrame:
    """Reshape a monthly trend so each calendar year becomes a series over months 1-12."""
    frame = monthly.assign(
        year=monthly["month_start"].dt.year.astype(str),
        month=monthly["month_start"].dt.month,
        month_label=monthly["month_start"].dt.strftime("%b"),
    )
    return frame[["year", "month", "month_label", "net_revenue", "orders"]].sort_values(
        ["year", "month"]
    )


def category_summary(lines: pd.DataFrame) -> pd.DataFrame:
    completed = completed_lines(lines)
    summary = (
        completed.groupby("category")
        .agg(
            orders=("order_id", "nunique"),
            units=("quantity", "sum"),
            returned_units=("returned_quantity", "sum"),
            net_revenue=("net_revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
        .reset_index()
    )
    total = summary["net_revenue"].sum()
    summary["share_of_net_revenue"] = summary["net_revenue"] / total if total else 0.0
    summary["gross_margin"] = [
        safe_ratio(profit, revenue)
        for profit, revenue in zip(summary["gross_profit"], summary["net_revenue"], strict=True)
    ]
    summary["return_rate"] = [
        safe_ratio(returned, units)
        for returned, units in zip(summary["returned_units"], summary["units"], strict=True)
    ]
    return summary.sort_values("net_revenue", ascending=False, ignore_index=True)


def top_products(lines: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    completed = completed_lines(lines)
    products = (
        completed.groupby(["product_id", "product_name", "category"])
        .agg(
            units=("quantity", "sum"),
            net_revenue=("net_revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
        )
        .reset_index()
        .sort_values(["net_revenue", "product_id"], ascending=[False, True])
    )
    return products.head(limit).reset_index(drop=True)


def repeat_rate_by(lines: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Repeat-purchase rate within the filtered window for each value of a customer attribute."""
    completed = completed_lines(lines)
    per_customer = (
        completed.groupby([dimension, "customer_key"])["order_id"].nunique().rename("orders")
    ).reset_index()
    grouped = (
        per_customer.groupby(dimension)
        .agg(
            customers=("customer_key", "count"),
            repeat_customers=("orders", lambda orders: int((orders >= 2).sum())),
        )
        .reset_index()
    )
    grouped["net_revenue"] = grouped[dimension].map(
        completed.groupby(dimension)["net_revenue"].sum()
    )
    grouped["repeat_purchase_rate"] = grouped["repeat_customers"] / grouped["customers"]
    grouped["net_revenue_per_customer"] = grouped["net_revenue"] / grouped["customers"]
    return grouped.sort_values("repeat_purchase_rate", ascending=False, ignore_index=True)


def customer_revenue(lines: pd.DataFrame) -> pd.Series:
    return completed_lines(lines).groupby("customer_key")["net_revenue"].sum()


def retention_matrix(cohorts: pd.DataFrame, max_offset: int = 12) -> pd.DataFrame:
    """Pivot cohort retention into cohort rows by month-offset columns."""
    subset = cohorts.loc[cohorts["months_since_first_order"] <= max_offset]
    matrix = subset.pivot(
        index="cohort_month", columns="months_since_first_order", values="retention_rate"
    )
    matrix.index = pd.to_datetime(matrix.index).strftime("%Y-%m")
    return matrix.sort_index()
