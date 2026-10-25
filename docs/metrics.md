# Metric definitions

All metrics are computed from the star schema described in [data_model.md](data_model.md).
The dbt models in `dbt/models/marts/metrics` are the system of record; the dashboard applies the
same formulas to filtered data through
[`metricflow_platform.metrics`](../src/metricflow_platform/metrics.py), and an integration test
checks that both produce identical totals.

## Conventions

- **Completed sales only.** Cancelled orders, and orders whose lines were all rejected during
  ingestion, are excluded from every metric (`fct_orders.is_completed_sale`,
  `fct_order_items.is_cancelled`).
- **Order-date basis.** Revenue, refunds, cost and profit are attributed to the UTC date of the
  original order. A refund issued in March for a January order reduces January's net revenue.
  Recent months can therefore still change as late returns arrive.
- **Currency.** The sample data has a single, unnamed currency. Taxes and shipping fees are not
  part of the dataset and are not included in any revenue figure.
- **Ratios are computed from totals**, never by averaging ratios: AOV for a quarter is total net
  sales divided by total orders in the quarter, not the mean of monthly AOVs.

## Revenue and profit

| Metric | Formula | Model |
| --- | --- | --- |
| Gross revenue (total revenue) | `sum(quantity * unit_price)` | `fct_order_items.gross_revenue` |
| Discounts | `sum(discount_amount)` | `fct_order_items.discount_amount` |
| Net sales | `gross revenue - discounts` | `fct_order_items.net_sales` |
| Refunds | `sum(refund_amount)` of returns for the line | `fct_order_items.refund_amount` |
| **Net revenue** | `net sales - refunds` | `fct_order_items.net_revenue` |
| Cost of goods sold | `(quantity - returned quantity) * unit_cost` | `fct_order_items.cost_of_goods_sold` |
| Gross profit | `net revenue - cost of goods sold` | `fct_order_items.gross_profit` |
| Gross margin | `gross profit / net revenue` | `mart_monthly_kpis.gross_margin` |

Assumptions and limitations:

- `unit_cost` is the cost of the product version valid on the order date (SCD Type 2), not the
  current cost.
- Returned units are assumed to be restocked at full cost, so their cost is removed from cost of
  goods sold. Handling costs, write-offs, payment fees and marketing spend are not available, so
  gross profit is a merchandise margin, not an operating profit.

## Orders and customers

| Metric | Formula | Model |
| --- | --- | --- |
| Order count | Number of completed sales | `mart_monthly_kpis.orders` |
| Average order value (AOV) | `net sales / order count` | `mart_monthly_kpis.average_order_value` |
| Active customers | Distinct customers with at least one completed sale in the period | `mart_monthly_kpis.active_customers` |
| New customers | Customers whose first completed sale falls in the period | `mart_monthly_kpis.new_customers` |
| Returning customers | `active customers - new customers` | `mart_monthly_kpis.returning_customers` |

AOV uses net sales (after discounts, before refunds) because refunds arrive after the order and
would otherwise make the AOV of recent periods drift.

When the dashboard filters by category, an order counts if it contains at least one line in the
selected categories, and AOV becomes *category net sales per order containing those
categories*.

## Repeat purchasing and lifetime value

| Metric | Formula | Model |
| --- | --- | --- |
| Repeat-purchase rate | Customers with 2 or more completed sales / customers with at least 1, within the same window | `mart_customer_metrics.is_repeat_customer`, dashboard |
| Frequency segment | `no_orders` (0), `one_time` (1), `repeat` (2-3), `loyal` (4+) lifetime completed sales | `mart_customer_metrics.frequency_segment` |
| Historical customer lifetime value | Sum of net revenue from the first order to the end of the data | `mart_customer_metrics.lifetime_net_revenue` |
| First-year value | Net revenue in the 365 days starting at the first order; only for customers whose first year is fully observed | `mart_customer_metrics.net_revenue_first_365d` |
| Cohort retention | Share of a first-order cohort with a completed sale N calendar months after the cohort month | `mart_cohort_retention.retention_rate` |

Customer lifetime value is **historical and observed**: it does not forecast future purchases,
apply churn probabilities or discount future cash flows, and it is based on net revenue, not
profit. Customers acquired recently have had less time to buy again, which lowers their
lifetime value and repeat rate (right-censoring). Compare cohorts with `net_revenue_first_365d`
or cohort retention at a fixed month offset rather than with lifetime totals.

## Product and category performance

| Metric | Formula | Model |
| --- | --- | --- |
| Category net revenue, profit, margin | Line measures grouped by product category and month | `mart_category_monthly` |
| Category share | Category net revenue / total net revenue of the month | `mart_category_monthly.share_of_month_net_revenue` |
| Product return rate | Returned units / units sold | `mart_product_performance.return_rate` |
| Six-month change | Net revenue in the last six months of data vs. the six months before, minus 1 | `mart_product_performance.net_revenue_6m_change` |
| Sales trend | `declining` below -20%, `growing` above +20%, otherwise `stable`; `new` without prior-window sales; `no_recent_sales` without sales in either window | `mart_product_performance.sales_trend` |

The ±20% thresholds are a reporting convention, not a statistical test; products with small
sales volumes can move between labels because of a handful of orders.

## Trends

| Metric | Formula | Model |
| --- | --- | --- |
| Month-over-month growth | `net revenue / previous month net revenue - 1` | `mart_monthly_kpis.net_revenue_mom_growth` |
| Year-over-year growth | `net revenue / same month previous year - 1`; null for the first year | `mart_monthly_kpis.net_revenue_yoy_growth`, `orders_yoy_growth` |

Months without orders are kept with zero values so that lagged comparisons always refer to the
correct calendar month.

## Revenue concentration

`metricflow_platform.metrics.top_share(values, fraction)` returns the share of total net revenue
held by the top `fraction` of customers or products (for example the top 10%). Negative values,
which can occur when refunds exceed sales for an entity, are treated as zero.
