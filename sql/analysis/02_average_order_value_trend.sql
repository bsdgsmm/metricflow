-- How does average order value change over time? Quarterly AOV with year-over-year change.
with quarterly as (
    select
        date_trunc('quarter', month_start)::date as quarter_start,
        sum(orders) as orders,
        sum(net_sales) as net_sales
    from marts.mart_monthly_kpis
    group by quarter_start
)

select
    to_char(quarter_start, 'YYYY-"Q"Q') as quarter_label,
    orders,
    round(net_sales / nullif(orders, 0), 2) as average_order_value,
    round(
        (net_sales / nullif(orders, 0))
        / nullif(lag(net_sales / nullif(orders, 0), 4) over (order by quarter_start), 0)
        - 1,
        4
    ) as aov_yoy_change
from quarterly
order by quarter_start;
