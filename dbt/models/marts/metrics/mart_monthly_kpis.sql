with months as (
    select distinct month_start
    from {{ ref('dim_date') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
    where is_completed_sale
),

monthly as (
    select
        date_trunc('month', order_date)::date as month_start,
        count(*) as orders,
        count(distinct customer_key) as active_customers,
        count(*) filter (where is_first_order) as new_customers,
        sum(units) as units,
        sum(gross_revenue) as gross_revenue,
        sum(discount_amount) as discount_amount,
        sum(net_sales) as net_sales,
        sum(refund_amount) as refund_amount,
        sum(net_revenue) as net_revenue,
        sum(cost_of_goods_sold) as cost_of_goods_sold,
        sum(gross_profit) as gross_profit
    from orders
    group by 1
),

filled as (
    select
        months.month_start,
        coalesce(monthly.orders, 0) as orders,
        coalesce(monthly.active_customers, 0) as active_customers,
        coalesce(monthly.new_customers, 0) as new_customers,
        coalesce(monthly.units, 0) as units,
        coalesce(monthly.gross_revenue, 0) as gross_revenue,
        coalesce(monthly.discount_amount, 0) as discount_amount,
        coalesce(monthly.net_sales, 0) as net_sales,
        coalesce(monthly.refund_amount, 0) as refund_amount,
        coalesce(monthly.net_revenue, 0) as net_revenue,
        coalesce(monthly.cost_of_goods_sold, 0) as cost_of_goods_sold,
        coalesce(monthly.gross_profit, 0) as gross_profit
    from months
    left join monthly
        on months.month_start = monthly.month_start
),

with_ratios as (
    select
        *,
        active_customers - new_customers as returning_customers,
        net_sales / nullif(orders, 0) as average_order_value,
        gross_profit / nullif(net_revenue, 0) as gross_margin,
        lag(net_revenue, 1) over (order by month_start) as net_revenue_prior_month,
        lag(net_revenue, 12) over (order by month_start) as net_revenue_prior_year,
        lag(orders, 12) over (order by month_start) as orders_prior_year
    from filled
)

select
    month_start,
    orders,
    active_customers,
    new_customers,
    returning_customers,
    units,
    gross_revenue,
    discount_amount,
    net_sales,
    refund_amount,
    net_revenue,
    cost_of_goods_sold,
    gross_profit,
    round(average_order_value, 2) as average_order_value,
    round(gross_margin, 4) as gross_margin,
    net_revenue_prior_month,
    round(net_revenue / nullif(net_revenue_prior_month, 0) - 1, 4) as net_revenue_mom_growth,
    net_revenue_prior_year,
    round(net_revenue / nullif(net_revenue_prior_year, 0) - 1, 4) as net_revenue_yoy_growth,
    orders_prior_year,
    round(orders::numeric / nullif(orders_prior_year, 0) - 1, 4) as orders_yoy_growth
from with_ratios
