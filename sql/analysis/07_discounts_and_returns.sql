-- How much revenue is lost to discounts and refunds in each category?
select
    category,
    sum(gross_revenue) as gross_revenue,
    round(sum(discount_amount) / nullif(sum(gross_revenue), 0), 4) as discount_rate,
    round(sum(refund_amount) / nullif(sum(net_sales), 0), 4) as refund_rate,
    round(sum(net_revenue) / nullif(sum(gross_revenue), 0), 4) as net_to_gross_ratio
from marts.mart_category_monthly
group by category
order by refund_rate desc;
