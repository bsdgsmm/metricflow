-- How concentrated is revenue across customers and products?
-- Share of total lifetime net revenue held by the top 1%, 10% and 20% of each population.
with customers as (
    select
        'customers' as population,
        lifetime_net_revenue as net_revenue,
        percent_rank() over (order by lifetime_net_revenue desc) as revenue_rank
    from marts.mart_customer_metrics
    where order_count > 0
),

products as (
    select
        'products' as population,
        net_revenue,
        percent_rank() over (order by net_revenue desc) as revenue_rank
    from marts.mart_product_performance
    where units > 0
),

ranked as (
    select
        population,
        net_revenue,
        revenue_rank
    from customers
    union all
    select
        population,
        net_revenue,
        revenue_rank
    from products
)

select
    population,
    count(*) as population_size,
    round(sum(net_revenue) filter (where revenue_rank < 0.01) / sum(net_revenue), 4)
        as top_1pct_share,
    round(sum(net_revenue) filter (where revenue_rank < 0.10) / sum(net_revenue), 4)
        as top_10pct_share,
    round(sum(net_revenue) filter (where revenue_rank < 0.20) / sum(net_revenue), 4)
        as top_20pct_share
from ranked
group by population
order by population;
