with orders as (
    select * from {{ ref('stg_orders') }}
),

lines as (
    select
        order_id,
        count(*) as line_count,
        sum(quantity) as units,
        sum(returned_quantity) as returned_units,
        sum(gross_revenue) as gross_revenue,
        sum(discount_amount) as discount_amount,
        sum(net_sales) as net_sales,
        sum(refund_amount) as refund_amount,
        sum(net_revenue) as net_revenue,
        sum(cost_of_goods_sold) as cost_of_goods_sold,
        sum(gross_profit) as gross_profit
    from {{ ref('int_order_lines_enriched') }}
    group by order_id
),

order_sequence as (
    select * from {{ ref('int_customer_order_sequence') }}
)

select
    orders.order_id,
    md5(orders.customer_id) as customer_key,
    orders.order_date,
    orders.ordered_at,
    orders.order_status,
    orders.is_cancelled,
    orders.order_channel,
    orders.payment_method,
    order_sequence.customer_order_number,
    coalesce(order_sequence.customer_order_number = 1, false) as is_first_order,
    order_sequence.days_since_previous_order,
    coalesce(lines.line_count, 0) as line_count,
    coalesce(lines.units, 0) as units,
    coalesce(lines.returned_units, 0) as returned_units,
    coalesce(lines.gross_revenue, 0) as gross_revenue,
    coalesce(lines.discount_amount, 0) as discount_amount,
    coalesce(lines.net_sales, 0) as net_sales,
    coalesce(lines.refund_amount, 0) as refund_amount,
    coalesce(lines.net_revenue, 0) as net_revenue,
    coalesce(lines.cost_of_goods_sold, 0) as cost_of_goods_sold,
    coalesce(lines.gross_profit, 0) as gross_profit
from orders
left join lines
    on orders.order_id = lines.order_id
left join order_sequence
    on orders.order_id = order_sequence.order_id
