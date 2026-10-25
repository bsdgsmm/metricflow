-- How well are customers retained? Customer-weighted retention at fixed month offsets by the
-- year of the first order, counting only cohorts old enough to have reached each offset.
select
    extract(year from cohort_month)::integer as cohort_year,
    months_since_first_order,
    count(*) as cohorts,
    sum(cohort_size) as customers,
    round(sum(active_customers)::numeric / sum(cohort_size), 4) as retention_rate
from marts.mart_cohort_retention
where months_since_first_order in (1, 3, 6, 12)
group by cohort_year, months_since_first_order
order by cohort_year, months_since_first_order;
