with bounds as (
    select
        date_trunc('year', min(order_date))::date as first_day,
        (date_trunc('year', max(order_date)) + interval '1 year - 1 day')::date as last_day
    from {{ ref('stg_orders') }}
),

days as (
    select generate_series(first_day, last_day, interval '1 day')::date as date_day
    from bounds
)

select
    date_day,
    extract(year from date_day)::integer as calendar_year,
    extract(quarter from date_day)::integer as calendar_quarter,
    extract(month from date_day)::integer as month_of_year,
    to_char(date_day, 'FMMonth') as month_name,
    to_char(date_day, 'YYYY-MM') as year_month_label,
    date_trunc('month', date_day)::date as month_start,
    date_trunc('week', date_day)::date as week_start,
    extract(isodow from date_day)::integer as iso_day_of_week,
    to_char(date_day, 'FMDay') as day_name,
    extract(isodow from date_day) in (6, 7) as is_weekend
from days
