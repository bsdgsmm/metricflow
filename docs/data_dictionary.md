# Data dictionary

## Raw layer (`raw` schema)

Tables are created by `python -m metricflow_platform init-db` (or automatically by `ingest`) from
the specifications in [`validation/schemas.py`](../src/metricflow_platform/validation/schemas.py).
Every source table also carries the lineage columns `_batch_id`, `_source_file`,
`_source_row_number` and `_loaded_at`.

### customers

| Column | Type | Required | Rules |
| --- | --- | --- | --- |
| `customer_id` | text | yes | Primary key |
| `signup_date` | date | yes | ISO `YYYY-MM-DD`, valid calendar date |
| `country` | text | yes | |
| `city` | text | yes | |
| `acquisition_channel` | text | yes | |
| `marketing_opt_in` | boolean | yes | true/false, t/f, 1/0, yes/no, y/n |

### products

| Column | Type | Required | Rules |
| --- | --- | --- | --- |
| `product_id` | text | yes | Primary key |
| `product_name` | text | yes | |
| `category` | text | yes | |
| `subcategory` | text | yes | |
| `brand` | text | yes | |
| `launched_on` | date | yes | |
| `discontinued_on` | date | no | |

### product_price_history

| Column | Type | Required | Rules |
| --- | --- | --- | --- |
| `product_id` | text | yes | Primary key part; must exist in `products` |
| `valid_from` | date | yes | Primary key part; version effective from this date |
| `list_price` | numeric(12, 2) | yes | >= 0 |
| `unit_cost` | numeric(12, 2) | yes | >= 0 |

### orders

| Column | Type | Required | Rules |
| --- | --- | --- | --- |
| `order_id` | text | yes | Primary key |
| `customer_id` | text | yes | Must exist in `customers` |
| `order_timestamp` | timestamptz | yes | ISO 8601 with a UTC offset (`Z` or `+hh:mm`) |
| `status` | text | yes | `completed` or `cancelled` |
| `channel` | text | yes | `web` or `mobile_app` |
| `payment_method` | text | yes | `card`, `paypal` or `gift_card` |

### order_items

| Column | Type | Required | Rules |
| --- | --- | --- | --- |
| `order_item_id` | text | yes | Primary key |
| `order_id` | text | yes | Must exist in `orders` |
| `product_id` | text | yes | Must exist in `products` |
| `quantity` | integer | yes | >= 1 |
| `unit_price` | numeric(12, 2) | yes | >= 0; price charged per unit |
| `discount_amount` | numeric(12, 2) | yes | >= 0 and <= `quantity * unit_price` |

### returns

| Column | Type | Required | Rules |
| --- | --- | --- | --- |
| `return_id` | text | yes | Primary key |
| `order_item_id` | text | yes | Must exist in `order_items` |
| `return_date` | date | yes | |
| `quantity` | integer | yes | >= 1 |
| `refund_amount` | numeric(12, 2) | yes | >= 0 |
| `reason` | text | yes | |

### Ingestion metadata

| Table | Grain | Key columns |
| --- | --- | --- |
| `rejected_records` | One row per rejected source line in the latest run of each file | `table_name`, `source_file`, `source_row_number`, `reason`, `detail`, `payload` (jsonb), `batch_id` |
| `ingestion_runs` | One row per table load attempt | `run_id`, `batch_id`, `table_name`, `status`, `file_sha256`, `rows_read`, `rows_inserted`, `rows_updated`, `rows_unchanged`, `rows_rejected`, `duplicates_removed`, `error_message`, `started_at`, `finished_at` |

Rejection reasons: `malformed_row`, `missing_required`, `invalid_integer`, `invalid_decimal`,
`invalid_date`, `invalid_timestamp`, `invalid_boolean`, `below_minimum`, `value_not_allowed`,
`discount_exceeds_line_amount`, `conflicting_duplicate_key`, `orphaned_foreign_key`.

## Staging layer (`staging` schema)

One view per source table with consistent names: `stg_customers`, `stg_products`,
`stg_product_prices`, `stg_orders`, `stg_order_items`, `stg_returns`. Notable derived columns:

| Model | Column | Definition |
| --- | --- | --- |
| `stg_customers` | `is_marketing_opt_in` | Renamed `marketing_opt_in` |
| `stg_products` | `is_active` | `discontinued_on is null` |
| `stg_orders` | `ordered_at` | Source `order_timestamp` |
| `stg_orders` | `order_date` | UTC calendar date of `ordered_at` |
| `stg_orders` | `is_cancelled` | `status = 'cancelled'` |
| `stg_order_items` | `gross_amount` | `quantity * unit_price` |
| `stg_returns` | `returned_on`, `returned_quantity`, `return_reason` | Renamed source columns |

## Intermediate layer (`intermediate` schema)

| Model | Grain | Purpose |
| --- | --- | --- |
| `int_product_versions` | Product price version | SCD2 versions with `valid_from`, exclusive `valid_to`, `version_number`, `is_current` |
| `int_order_lines_enriched` | Order line | Product version valid on the order date, aggregated returns and all line measures |
| `int_customer_order_sequence` | Completed sale | `customer_order_number`, `days_since_previous_order` |

## Marts (`marts` schema)

Column-level descriptions and tests for every mart live in the dbt YAML files
([`_core.yml`](../dbt/models/marts/core/_core.yml), [`_metrics.yml`](../dbt/models/marts/metrics/_metrics.yml))
and can be browsed with `python -m metricflow_platform dbt docs generate` followed by
`python -m metricflow_platform dbt docs serve`.

| Model | Grain | Description |
| --- | --- | --- |
| `dim_customers` | Customer | Attributes, signup month, first-order date and month (cohort) |
| `dim_products` | Product price version | SCD Type 2 product dimension |
| `dim_date` | Calendar day | Year, quarter, month, week and weekday attributes |
| `fct_order_items` | Order line | Additive revenue, cost and profit measures; `is_cancelled` flag |
| `fct_orders` | Order | Order attributes, `is_completed_sale`, customer order sequence, aggregated measures |
| `mart_monthly_kpis` | Month | KPIs with MoM and YoY growth |
| `mart_category_monthly` | Month and category | Category revenue, profit, margin and share |
| `mart_product_performance` | Product | Lifetime metrics, return rate, six-month trend |
| `mart_customer_metrics` | Customer | Order counts, frequency segment, historical lifetime value |
| `mart_cohort_retention` | Cohort month and month offset | Retention rate |
