with lines as (
    select
        date_trunc('month', items.order_date)::date as month_start,
        products.category,
        items.order_id,
        items.quantity,
        items.gross_revenue,
        items.discount_amount,
        items.net_sales,
        items.refund_amount,
        items.net_revenue,
        items.cost_of_goods_sold,
        items.gross_profit
    from {{ ref('fct_order_items') }} as items
    inner join {{ ref('dim_products') }} as products
        on items.product_key = products.product_key
    where not items.is_cancelled
),

aggregated as (
    select
        month_start,
        category,
        count(distinct order_id) as orders,
        sum(quantity) as units,
        sum(gross_revenue) as gross_revenue,
        sum(discount_amount) as discount_amount,
        sum(net_sales) as net_sales,
        sum(refund_amount) as refund_amount,
        sum(net_revenue) as net_revenue,
        sum(cost_of_goods_sold) as cost_of_goods_sold,
        sum(gross_profit) as gross_profit
    from lines
    group by month_start, category
)

select
    month_start,
    category,
    orders,
    units,
    gross_revenue,
    discount_amount,
    net_sales,
    refund_amount,
    net_revenue,
    cost_of_goods_sold,
    gross_profit,
    round(gross_profit / nullif(net_revenue, 0), 4) as gross_margin,
    round(
        net_revenue / nullif(sum(net_revenue) over (partition by month_start), 0), 4
    ) as share_of_month_net_revenue
from aggregated
