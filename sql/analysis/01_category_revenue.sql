-- Which product categories generate the most revenue, and how profitable are they?
select
    category,
    sum(net_revenue) as net_revenue,
    round(sum(net_revenue) / sum(sum(net_revenue)) over (), 4) as share_of_net_revenue,
    sum(gross_profit) as gross_profit,
    round(sum(gross_profit) / nullif(sum(net_revenue), 0), 4) as gross_margin,
    sum(orders) as category_orders
from marts.mart_category_monthly
group by category
order by net_revenue desc;
