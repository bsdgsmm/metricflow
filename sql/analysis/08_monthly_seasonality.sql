-- Is there a seasonal pattern? Average monthly net revenue relative to each year's monthly mean.
with indexed as (
    select
        extract(year from month_start)::integer as calendar_year,
        extract(month from month_start)::integer as month_of_year,
        net_revenue / avg(net_revenue) over (partition by date_trunc('year', month_start))
            as seasonal_index
    from marts.mart_monthly_kpis
)

select
    month_of_year,
    round(avg(seasonal_index), 3) as avg_seasonal_index,
    round(min(seasonal_index), 3) as min_seasonal_index,
    round(max(seasonal_index), 3) as max_seasonal_index
from indexed
group by month_of_year
order by month_of_year;
