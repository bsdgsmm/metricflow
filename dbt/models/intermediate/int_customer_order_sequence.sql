with orders as (
    select * from {{ ref('stg_orders') }}
    where not is_cancelled
)

select
    order_id,
    customer_id,
    ordered_at,
    order_date,
    row_number() over (
        partition by customer_id
        order by ordered_at, order_id
    ) as customer_order_number,
    order_date - lag(order_date) over (
        partition by customer_id
        order by ordered_at, order_id
    ) as days_since_previous_order
from orders
