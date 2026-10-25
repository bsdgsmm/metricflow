{{ config(severity='warn') }}

-- Orders whose lines were all rejected at ingestion. They are excluded from sales metrics
-- through fct_orders.is_completed_sale; a warning keeps them visible for investigation.
select
    order_id,
    order_status
from {{ ref('fct_orders') }}
where line_count = 0
