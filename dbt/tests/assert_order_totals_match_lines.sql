-- Order-level measures must equal the sum of their lines.
with lines as (
    select
        order_id,
        sum(net_sales) as net_sales,
        sum(net_revenue) as net_revenue,
        sum(gross_profit) as gross_profit,
        sum(quantity) as units
    from {{ ref('fct_order_items') }}
    group by order_id
)

select
    orders.order_id,
    orders.net_revenue,
    lines.net_revenue as line_net_revenue
from {{ ref('fct_orders') }} as orders
left join lines
    on orders.order_id = lines.order_id
where
    orders.net_sales != coalesce(lines.net_sales, 0)
    or orders.net_revenue != coalesce(lines.net_revenue, 0)
    or orders.gross_profit != coalesce(lines.gross_profit, 0)
    or orders.units != coalesce(lines.units, 0)
