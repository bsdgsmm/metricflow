{% set trend_window_months = 6 %}

with as_of as (
    select date_trunc('month', max(order_date))::date as last_month
    from {{ ref('fct_orders') }}
),

lines as (
    select
        products.product_id,
        items.order_date,
        items.quantity,
        items.returned_quantity,
        items.net_sales,
        items.net_revenue,
        items.gross_profit
    from {{ ref('fct_order_items') }} as items
    inner join {{ ref('dim_products') }} as products
        on items.product_key = products.product_key
    where not items.is_cancelled
),

windowed as (
    select
        lines.*,
        lines.order_date
        >= as_of.last_month - interval '{{ trend_window_months - 1 }} months' as is_recent,
        lines.order_date
        >= as_of.last_month - interval '{{ 2 * trend_window_months - 1 }} months'
        and lines.order_date
        < as_of.last_month - interval '{{ trend_window_months - 1 }} months' as is_prior
    from lines
    cross join as_of
),

aggregated as (
    select
        product_id,
        min(order_date) as first_sold_on,
        max(order_date) as last_sold_on,
        sum(quantity) as units,
        sum(returned_quantity) as returned_units,
        sum(net_sales) as net_sales,
        sum(net_revenue) as net_revenue,
        sum(gross_profit) as gross_profit,
        coalesce(sum(net_revenue) filter (where is_recent), 0) as net_revenue_recent_6m,
        coalesce(sum(net_revenue) filter (where is_prior), 0) as net_revenue_prior_6m
    from windowed
    group by product_id
),

current_products as (
    select * from {{ ref('dim_products') }}
    where is_current
)

select
    current_products.product_id,
    current_products.product_name,
    current_products.category,
    current_products.subcategory,
    current_products.brand,
    current_products.list_price as current_list_price,
    current_products.launched_on,
    current_products.discontinued_on,
    current_products.is_active,
    aggregated.first_sold_on,
    aggregated.last_sold_on,
    coalesce(aggregated.units, 0) as units,
    coalesce(aggregated.returned_units, 0) as returned_units,
    round(aggregated.returned_units::numeric / nullif(aggregated.units, 0), 4) as return_rate,
    coalesce(aggregated.net_sales, 0) as net_sales,
    coalesce(aggregated.net_revenue, 0) as net_revenue,
    coalesce(aggregated.gross_profit, 0) as gross_profit,
    round(aggregated.gross_profit / nullif(aggregated.net_revenue, 0), 4) as gross_margin,
    coalesce(aggregated.net_revenue_recent_6m, 0) as net_revenue_recent_6m,
    coalesce(aggregated.net_revenue_prior_6m, 0) as net_revenue_prior_6m,
    round(
        aggregated.net_revenue_recent_6m / nullif(aggregated.net_revenue_prior_6m, 0) - 1, 4
    ) as net_revenue_6m_change,
    case
        when
            coalesce(aggregated.net_revenue_recent_6m, 0) = 0
            and coalesce(aggregated.net_revenue_prior_6m, 0) = 0
            then 'no_recent_sales'
        when coalesce(aggregated.net_revenue_prior_6m, 0) = 0
            then 'new'
        when aggregated.net_revenue_recent_6m < 0.8 * aggregated.net_revenue_prior_6m
            then 'declining'
        when aggregated.net_revenue_recent_6m > 1.2 * aggregated.net_revenue_prior_6m
            then 'growing'
        else 'stable'
    end as sales_trend
from current_products
left join aggregated
    on current_products.product_id = aggregated.product_id
