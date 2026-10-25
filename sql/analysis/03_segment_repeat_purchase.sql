-- Which customer segments have the strongest repeat-purchase behaviour?
-- Lifetime repeat rate is right-censored for recent customers, so the first-year view restricts
-- the comparison to customers whose first 365 days are fully observed.
select
    acquisition_channel,
    count(*) as purchasing_customers,
    round(avg(case when is_repeat_customer then 1.0 else 0 end), 4) as lifetime_repeat_rate,
    round(avg(lifetime_net_revenue), 2) as avg_lifetime_net_revenue,
    count(*) filter (where has_full_first_year) as customers_with_full_first_year,
    round(avg(net_revenue_first_365d) filter (where has_full_first_year), 2)
        as avg_first_year_net_revenue
from marts.mart_customer_metrics
where order_count > 0
group by acquisition_channel
order by lifetime_repeat_rate desc;
