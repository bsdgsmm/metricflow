-- By definition every customer orders in their cohort month, so month 0 retention must be 100%.
select
    cohort_month,
    cohort_size,
    active_customers,
    retention_rate
from {{ ref('mart_cohort_retention') }}
where months_since_first_order = 0 and retention_rate != 1
