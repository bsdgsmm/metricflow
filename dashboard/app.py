"""MetricFlow executive dashboard.

Run with: streamlit run dashboard/app.py
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd
import psycopg
import streamlit as st

from metricflow_platform.config import ConfigurationError, load_settings
from metricflow_platform.dashboard import analysis, charts, formatting
from metricflow_platform.dashboard.queries import (
    COHORT_RETENTION,
    CUSTOMER_METRICS,
    DATA_EXTENT,
    ORDER_LINES,
    PRODUCT_PERFORMANCE,
    fetch_frame,
)
from metricflow_platform.database import DatabaseUnavailableError, connect
from metricflow_platform.metrics import KpiSummary, summarize_kpis, top_share

logger = logging.getLogger("metricflow_platform.dashboard")

st.set_page_config(page_title="MetricFlow", layout="wide")


@st.cache_data(ttl=600, show_spinner="Loading data from the warehouse...")
def load_data() -> dict[str, pd.DataFrame]:
    settings = load_settings()
    with connect(settings.database, attempts=3) as conn:
        return {
            "lines": fetch_frame(conn, ORDER_LINES),
            "products": fetch_frame(conn, PRODUCT_PERFORMANCE),
            "customers": fetch_frame(conn, CUSTOMER_METRICS),
            "cohorts": fetch_frame(conn, COHORT_RETENTION),
            "extent": fetch_frame(conn, DATA_EXTENT),
        }


MONEY = st.column_config.NumberColumn(format="localized")
RATE = st.column_config.NumberColumn(format="percent")
COLUMN_FORMATS = {
    "net_sales": MONEY,
    "net_revenue": MONEY,
    "gross_profit": MONEY,
    "average_order_value": MONEY,
    "net_revenue_per_customer": MONEY,
    "net_revenue_recent_6m": MONEY,
    "net_revenue_prior_6m": MONEY,
    "gross_margin": RATE,
    "share_of_net_revenue": RATE,
    "return_rate": RATE,
    "repeat_purchase_rate": RATE,
    "net_revenue_6m_change": RATE,
}


def table(frame: pd.DataFrame) -> None:
    formats = {name: fmt for name, fmt in COLUMN_FORMATS.items() if name in frame.columns}
    formats.update({c: RATE for c in frame.columns if str(c).startswith("month_")})
    st.dataframe(frame, hide_index=True, width="stretch", column_config=formats)


def show_table(frame: pd.DataFrame, label: str = "Show data") -> None:
    with st.expander(label):
        table(frame)


def kpi_row(current: KpiSummary, previous: KpiSummary) -> None:
    columns = st.columns(6)
    columns[0].metric(
        "Net revenue",
        formatting.currency(current.net_revenue),
        formatting.change(current.net_revenue, previous.net_revenue),
        help="Net sales minus refunds, completed sales only.",
    )
    columns[1].metric(
        "Orders",
        formatting.integer(current.orders),
        formatting.change(current.orders, previous.orders),
        help="Number of completed sales.",
    )
    columns[2].metric(
        "Average order value",
        formatting.currency_precise(current.average_order_value),
        formatting.change(current.average_order_value, previous.average_order_value),
        help="Net sales divided by orders.",
    )
    columns[3].metric(
        "Gross margin",
        formatting.percent(current.gross_margin),
        formatting.point_change(current.gross_margin, previous.gross_margin),
        help="Gross profit divided by net revenue.",
    )
    columns[4].metric(
        "Active customers",
        formatting.integer(current.customers),
        formatting.change(current.customers, previous.customers),
        help="Distinct customers with at least one completed sale.",
    )
    columns[5].metric(
        "Repeat-purchase rate",
        formatting.percent(current.repeat_purchase_rate),
        formatting.point_change(current.repeat_purchase_rate, previous.repeat_purchase_rate),
        help="Share of active customers with two or more orders in the selected period.",
    )


def overview_tab(lines: pd.DataFrame, previous_lines: pd.DataFrame, period: str) -> None:
    kpi_row(summarize_kpis(lines), summarize_kpis(previous_lines))
    st.caption(f"Deltas compare with the previous period of equal length ({period}).")

    monthly = analysis.monthly_trend(lines)
    left, right = st.columns(2)
    left.plotly_chart(
        charts.monthly_bars(
            monthly, "net_revenue", title="Net revenue by month", y_title="Net revenue"
        ),
        width="stretch",
    )
    right.plotly_chart(
        charts.monthly_bars(
            monthly, "orders", title="Orders by month", y_title="Orders", y_format=",d"
        ),
        width="stretch",
    )
    show_table(monthly, "Show monthly data")


def trends_tab(lines: pd.DataFrame, all_dates: pd.DataFrame) -> None:
    monthly = analysis.monthly_trend(lines)
    left, right = st.columns(2)
    left.plotly_chart(
        charts.monthly_line(
            monthly,
            "average_order_value",
            title="Average order value",
            y_title="Average order value",
            y_format=",.2f",
        ),
        width="stretch",
    )
    right.plotly_chart(
        charts.monthly_line(
            monthly, "gross_margin", title="Gross margin", y_title="Gross margin", y_format=".0%"
        ),
        width="stretch",
    )
    show_table(monthly, "Show monthly data")

    st.subheader("Year-over-year comparison")
    st.caption("Uses every available month so years can be compared; category filter applied.")
    yoy = analysis.year_over_year(analysis.monthly_trend(all_dates))
    if yoy["year"].nunique() < 2:
        st.info("At least two calendar years of data are needed for a year-over-year comparison.")
    else:
        st.plotly_chart(
            charts.year_over_year_lines(
                yoy, "net_revenue", title="Net revenue by month and year", y_title="Net revenue"
            ),
            width="stretch",
        )
        show_table(yoy, "Show year-over-year data")


def products_tab(lines: pd.DataFrame, products: pd.DataFrame) -> None:
    categories = analysis.category_summary(lines)
    left, right = st.columns(2)
    left.plotly_chart(
        charts.ranked_bars(
            categories,
            "category",
            "net_revenue",
            title="Net revenue by category",
            x_title="Net revenue",
        ),
        width="stretch",
    )
    right.plotly_chart(
        charts.ranked_bars(
            categories,
            "category",
            "gross_margin",
            title="Gross margin by category",
            x_title="Gross margin",
            x_format=".1%",
        ),
        width="stretch",
    )
    show_table(categories, "Show category data")

    st.subheader("Top products in the selected period")
    table(analysis.top_products(lines))

    st.subheader("Declining products")
    st.caption(
        "Net revenue in the last six months of data compared with the six months before "
        "(fixed window, all dates; category filter applied)."
    )
    declining = products.loc[products["sales_trend"] == "declining"]
    selected = lines["category"].unique()
    declining = declining.loc[declining["category"].isin(selected)].sort_values(
        "net_revenue_6m_change"
    )
    if declining.empty:
        st.info("No declining products in the selected categories.")
    else:
        table(
            declining[
                [
                    "product_id",
                    "product_name",
                    "category",
                    "is_active",
                    "net_revenue_prior_6m",
                    "net_revenue_recent_6m",
                    "net_revenue_6m_change",
                ]
            ]
        )


def customers_tab(lines: pd.DataFrame, customers: pd.DataFrame, cohorts: pd.DataFrame) -> None:
    by_channel = analysis.repeat_rate_by(lines, "acquisition_channel")
    by_country = analysis.repeat_rate_by(lines, "country")
    left, right = st.columns(2)
    left.plotly_chart(
        charts.ranked_bars(
            by_channel,
            "acquisition_channel",
            "repeat_purchase_rate",
            title="Repeat-purchase rate by acquisition channel",
            x_title="Repeat-purchase rate",
            x_format=".1%",
        ),
        width="stretch",
    )
    right.plotly_chart(
        charts.ranked_bars(
            by_country,
            "country",
            "repeat_purchase_rate",
            title="Repeat-purchase rate by country",
            x_title="Repeat-purchase rate",
            x_format=".1%",
        ),
        width="stretch",
    )
    show_table(pd.concat([by_channel, by_country]), "Show segment data")

    revenue = analysis.customer_revenue(lines)
    columns = st.columns(3)
    columns[0].metric(
        "Top 10% of customers' share of net revenue", formatting.percent(top_share(revenue, 0.10))
    )
    columns[1].metric(
        "Top 20% of customers' share of net revenue", formatting.percent(top_share(revenue, 0.20))
    )
    columns[2].metric(
        "Net revenue per active customer",
        formatting.currency_precise(revenue.mean() if len(revenue) else None),
    )

    st.subheader("Lifetime view (all dates and categories)")
    observed = customers.loc[customers["has_full_first_year"]]
    first_year = (
        observed.groupby("acquisition_channel")["net_revenue_first_365d"]
        .mean()
        .reset_index(name="first_year_value")
    )
    segments = (
        customers.groupby("frequency_segment")
        .size()
        .reindex(["no_orders", "one_time", "repeat", "loyal"], fill_value=0)
        .reset_index(name="customers")
    )
    left, right = st.columns(2)
    left.plotly_chart(
        charts.ranked_bars(
            first_year,
            "acquisition_channel",
            "first_year_value",
            title="Average first-year net revenue by channel",
            x_title="Net revenue in first 365 days",
        ),
        width="stretch",
    )
    right.plotly_chart(
        charts.ranked_bars(
            segments,
            "frequency_segment",
            "customers",
            title="Customers by lifetime order frequency",
            x_title="Customers",
            x_format=",d",
        ),
        width="stretch",
    )
    st.caption(
        "First-year value only includes customers whose first 365 days are fully observed. "
        "Frequency segments: one_time = 1 order, repeat = 2-3, loyal = 4 or more."
    )
    matrix = analysis.retention_matrix(cohorts)
    st.plotly_chart(
        charts.retention_heatmap(matrix, title="Monthly retention by first-order cohort"),
        width="stretch",
    )
    show_table(
        matrix.rename(columns=lambda offset: f"month_{offset}").reset_index(),
        "Show retention data",
    )


def main() -> None:
    st.title("MetricFlow")
    st.caption("Analytics for a fictional online retailer. All figures come from synthetic data.")

    try:
        data = load_data()
    except ConfigurationError as exc:
        st.error(f"Configuration problem: {exc}. Copy .env.example to .env and set the values.")
        st.stop()
    except DatabaseUnavailableError:
        logger.exception("dashboard_database_unavailable")
        st.error(
            "Cannot reach PostgreSQL. Check the METRICFLOW_DB_* settings and that the database "
            "is running."
        )
        st.stop()
    except psycopg.errors.UndefinedTable:
        st.warning(
            "The analytics tables do not exist yet. Load the data and build the models with "
            "`python -m metricflow_platform ingest` and `python -m metricflow_platform dbt build`."
        )
        st.stop()

    lines = data["lines"]
    if lines.empty:
        st.info("The warehouse contains no order lines yet. Run the ingestion pipeline first.")
        st.stop()

    first_day = data["extent"].loc[0, "first_order_date"].date()
    last_day = data["extent"].loc[0, "last_order_date"].date()
    all_categories = sorted(lines["category"].unique())

    with st.sidebar:
        st.header("Filters")
        selected_range = st.date_input(
            "Order date range",
            value=(date(last_day.year, 1, 1), last_day),
            min_value=first_day,
            max_value=last_day,
        )
        categories = st.multiselect(
            "Product categories", all_categories, placeholder="All categories"
        )
        st.caption(f"Data available from {first_day:%d %b %Y} to {last_day:%d %b %Y}.")

    if not isinstance(selected_range, tuple) or len(selected_range) != 2:
        st.info("Select both a start and an end date.")
        st.stop()
    start, end = selected_range
    previous_start, previous_end = analysis.previous_period(start, end)

    filtered = analysis.filter_lines(lines, start, end, categories)
    all_dates = analysis.filter_lines(lines, first_day, last_day, categories)
    previous = analysis.filter_lines(lines, previous_start, previous_end, categories)
    if filtered.loc[~filtered["is_cancelled"]].empty:
        st.info(
            "No completed sales match the selected filters. Widen the date range or clear "
            "the category filter."
        )
        st.stop()

    period = f"{previous_start:%d %b %Y} - {previous_end:%d %b %Y}"
    overview, trends, products, customers = st.tabs(
        ["Overview", "Trends", "Products & categories", "Customers"]
    )
    with overview:
        overview_tab(filtered, previous, period)
    with trends:
        trends_tab(filtered, all_dates)
    with products:
        products_tab(filtered, data["products"])
    with customers:
        customers_tab(filtered, data["customers"], data["cohorts"])


main()
