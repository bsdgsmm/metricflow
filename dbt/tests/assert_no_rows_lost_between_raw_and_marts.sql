-- Transformations must neither drop nor duplicate rows or revenue loaded by ingestion.
with checks as (
    select
        'order_items' as entity,
        (select count(*) from {{ source('raw', 'order_items') }}) as raw_rows,
        (select count(*) from {{ ref('fct_order_items') }}) as mart_rows
    union all
    select
        'orders' as entity,
        (select count(*) from {{ source('raw', 'orders') }}) as raw_rows,
        (select count(*) from {{ ref('fct_orders') }}) as mart_rows
    union all
    select
        'customers' as entity,
        (select count(*) from {{ source('raw', 'customers') }}) as raw_rows,
        (select count(*) from {{ ref('dim_customers') }}) as mart_rows
    union all
    select
        'product_versions' as entity,
        (select count(*) from {{ source('raw', 'product_price_history') }}) as raw_rows,
        (select count(*) from {{ ref('dim_products') }}) as mart_rows
    union all
    select
        'gross_revenue_cents' as entity,
        (
            select round(sum(quantity * unit_price) * 100)::bigint
            from {{ source('raw', 'order_items') }}
        ) as raw_rows,
        (
            select round(sum(gross_revenue) * 100)::bigint
            from {{ ref('fct_order_items') }}
        ) as mart_rows
)

select
    entity,
    raw_rows,
    mart_rows
from checks
where raw_rows != mart_rows
