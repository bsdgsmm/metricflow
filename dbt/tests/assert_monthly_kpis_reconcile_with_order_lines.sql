-- Monthly KPIs and category totals must add up to the line-level fact for every month.
with lines as (
    select
        date_trunc('month', order_date)::date as month_start,
        sum(net_revenue) as net_revenue,
        sum(gross_profit) as gross_profit
    from {{ ref('fct_order_items') }}
    where not is_cancelled
    group by month_start
),

categories as (
    select
        month_start,
        sum(net_revenue) as net_revenue
    from {{ ref('mart_category_monthly') }}
    group by month_start
)

select
    kpis.month_start,
    kpis.net_revenue as kpi_net_revenue,
    lines.net_revenue as line_net_revenue,
    categories.net_revenue as category_net_revenue
from {{ ref('mart_monthly_kpis') }} as kpis
left join lines
    on kpis.month_start = lines.month_start
left join categories
    on kpis.month_start = categories.month_start
where
    kpis.net_revenue != coalesce(lines.net_revenue, 0)
    or kpis.gross_profit != coalesce(lines.gross_profit, 0)
    or kpis.net_revenue != coalesce(categories.net_revenue, 0)
