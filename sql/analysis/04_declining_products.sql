-- Which products show declining sales? Compares full calendar years so that seasonality does
-- not distort the comparison, and ignores products with negligible prior-year revenue.
with yearly as (
    select
        products.product_id,
        extract(year from items.order_date)::integer as order_year,
        sum(items.net_revenue) as net_revenue
    from marts.fct_order_items as items
    inner join marts.dim_products as products
        on items.product_key = products.product_key
    where not items.is_cancelled
    group by products.product_id, order_year
),

compared as (
    select
        product_id,
        coalesce(sum(net_revenue) filter (where order_year = 2024), 0) as net_revenue_2024,
        coalesce(sum(net_revenue) filter (where order_year = 2025), 0) as net_revenue_2025
    from yearly
    group by product_id
)

select
    current_products.product_id,
    current_products.product_name,
    current_products.category,
    current_products.discontinued_on,
    compared.net_revenue_2024,
    compared.net_revenue_2025,
    round(compared.net_revenue_2025 / compared.net_revenue_2024 - 1, 4) as yoy_change
from compared
inner join marts.dim_products as current_products
    on
        compared.product_id = current_products.product_id
        and current_products.is_current
where
    compared.net_revenue_2024 >= 1000
    and compared.net_revenue_2025 < 0.8 * compared.net_revenue_2024
order by yoy_change;
