# Business insights

This document answers a set of business questions with the SQL in [`sql/analysis`](../sql/analysis).
Each finding below was produced by running that query against the marts built from the included
sample dataset (`data/sample`, seed `20230101`).

> **Read these as results of a simulation.** The dataset is synthetic. Several patterns, such as
> channel-dependent repeat purchasing, seasonality and product lifecycles, are parameters of the
> [generator](../src/metricflow_platform/sample_data.py), so the queries recover behaviour that
> was designed in. They demonstrate the analysis, not facts about any real business.

To reproduce, build the project and run, for example:

```bash
psql -h localhost -U metricflow -d metricflow -f sql/analysis/01_category_revenue.sql
```

## Example questions

| # | Question | Query |
| --- | --- | --- |
| 1 | Which product categories generate the most revenue? | [01_category_revenue.sql](../sql/analysis/01_category_revenue.sql) |
| 2 | How does average order value change over time? | [02_average_order_value_trend.sql](../sql/analysis/02_average_order_value_trend.sql) |
| 3 | Which customer segments have the strongest repeat-purchase behaviour? | [03_segment_repeat_purchase.sql](../sql/analysis/03_segment_repeat_purchase.sql) |
| 4 | Which products show declining sales? | [04_declining_products.sql](../sql/analysis/04_declining_products.sql) |
| 5 | How concentrated is revenue across customers and products? | [05_revenue_concentration.sql](../sql/analysis/05_revenue_concentration.sql) |
| 6 | How well are customers retained after their first order? | [06_cohort_retention_summary.sql](../sql/analysis/06_cohort_retention_summary.sql) |
| 7 | How much revenue is lost to discounts and refunds per category? | [07_discounts_and_returns.sql](../sql/analysis/07_discounts_and_returns.sql) |
| 8 | Is there a seasonal pattern? | [08_monthly_seasonality.sql](../sql/analysis/08_monthly_seasonality.sql) |

Supporting data quality queries live in [`sql/investigations`](../sql/investigations).

## Calculated findings

All amounts are in the dataset's single, unnamed currency and cover 2023-01-01 to 2025-12-31.

### 1. Category revenue

| Category | Net revenue | Share | Gross margin |
| --- | ---: | ---: | ---: |
| Electronics | 416,417 | 39.4% | 25.0% |
| Home & Kitchen | 181,898 | 17.2% | 46.9% |
| Sports & Outdoors | 168,921 | 16.0% | 40.7% |
| Apparel | 135,221 | 12.8% | 54.6% |
| Beauty | 101,784 | 9.6% | 65.3% |
| Books | 51,875 | 4.9% | 40.7% |

Electronics brings in the most revenue but has the lowest margin. In gross profit it is still
first (104,218), while Home & Kitchen (85,254), Apparel (73,777) and Beauty (66,438) are much
closer to it than their revenue shares suggest.

### 2. Average order value over time

Quarterly AOV ranged from 137.86 (2024-Q3) to 167.52 (2023-Q1) and showed no sustained trend:
year-over-year changes alternate between -11.7% and +14.8%. Order volume more than quadrupled
from 227 orders in 2023-Q1 to 1,073 in 2025-Q4, so growth came from more orders, not larger
baskets.

### 3. Repeat purchasing by acquisition channel

| Channel | Purchasing customers | Lifetime repeat rate | Avg first-year net revenue* |
| --- | ---: | ---: | ---: |
| referral | 415 | 64.8% | 390.12 |
| email | 422 | 56.2% | 348.08 |
| organic_search | 1,230 | 48.6% | 277.75 |
| paid_search | 901 | 38.1% | 240.04 |
| paid_social | 798 | 29.2% | 187.75 |
| affiliate | 361 | 27.4% | 212.60 |

\* Customers whose first 365 days are fully observed (between 200 and 685 per channel).

Referral and email customers repeat roughly twice as often as paid-social and affiliate
customers, and the first-year value comparison, which is free of right-censoring, keeps the same
order except that affiliate edges out paid social.

### 4. Declining products

Comparing full-year 2025 with 2024 (products with at least 1,000 net revenue in 2024), **14
products** declined by more than 20%. The largest drops were P0093 Velocity Everyday Yoga Mat
(-100%, discontinued on 2024-12-12), P0045 Casa Nova Essential Storage Box (-72.0%) and P0003
Voltix Premium Keyboard (-49.5%). The highest-revenue decliner is P0032 Oakline Ultra Knife Set
(7,870 to 5,560, -29.4%).

The dashboard's six-month trend label (`mart_product_performance.sales_trend`) flags 31 products
as declining, more than double this count. The difference comes from volume, not from the
method: the label has no minimum-revenue threshold, and 10 of the 31 had less than 200 net
revenue in the prior six months, so a few orders decide their label. Only 14 of them had at least
500 in the prior window. The label also compares July–December 2025 with January–June 2025; total
net revenue was 32% higher in the second half (281,949 vs 212,877), so products that fall on
that comparison are falling against a seasonal tailwind. Apply a volume threshold and a
same-season comparison before acting on a product's trend label.

### 5. Revenue concentration

| Population | Size | Top 1% share | Top 10% share | Top 20% share |
| --- | ---: | ---: | ---: | ---: |
| Customers | 4,127 | 6.0% | 33.6% | 52.4% |
| Products | 120 | 12.2% | 43.3% | 61.9% |

Revenue is moderately concentrated: the top fifth of customers accounts for just over half of
net revenue, and the top fifth of products for about three fifths.

### 6. Cohort retention

| First-order year | Month 1 | Month 3 | Month 6 | Month 12 |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 10.6% | 9.1% | 5.7% | 2.4% |
| 2024 | 12.3% | 9.1% | 4.9% | 3.6% |
| 2025 | 11.0% | 10.4% | 7.4% | n/a |

Around one customer in nine buys again in the month after their first order; activity in any
single later month falls to roughly 3% after a year. 2025 values at months 3 and 6 only include
cohorts old enough to have reached those offsets.

### 7. Discounts and refunds

Discounts take 2.6–3.1% of gross revenue in every category. Refunds vary far more: Apparel loses
9.5% of net sales to refunds, Electronics 5.1%, and Books 1.0%. Apparel keeps the lowest share of
its gross revenue as net revenue (88.0%).

### 8. Seasonality

Relative to each year's monthly average, net revenue rises steadily through the year from a
January low (index 0.65) to a December peak (1.39), with November at 1.23. Part of this slope is
growth within each year rather than seasonality, which this simple index does not separate.
