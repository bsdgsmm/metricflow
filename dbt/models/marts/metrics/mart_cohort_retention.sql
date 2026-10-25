with as_of as (
    select date_trunc('month', max(order_date))::date as last_month
    from {{ ref('fct_orders') }}
),

customers as (
    select
        customer_key,
        first_order_month as cohort_month
    from {{ ref('dim_customers') }}
    where first_order_month is not null
),

cohort_sizes as (
    select
        cohort_month,
        count(*) as cohort_size
    from customers
    group by cohort_month
),

activity as (
    select distinct
        orders.customer_key,
        customers.cohort_month,
        {{ months_between('orders.order_date', 'customers.cohort_month') }}
            as months_since_first_order
    from {{ ref('fct_orders') }} as orders
    inner join customers
        on orders.customer_key = customers.customer_key
    where orders.is_completed_sale
),

offsets as (
    select
        cohort_sizes.cohort_month,
        cohort_sizes.cohort_size,
        offset_month.months_since_first_order
    from cohort_sizes
    cross join as_of
    cross join lateral generate_series(
        0, {{ months_between('as_of.last_month', 'cohort_sizes.cohort_month') }}
    ) as offset_month (months_since_first_order)
)

select
    offsets.cohort_month,
    offsets.months_since_first_order,
    offsets.cohort_size,
    count(activity.customer_key) as active_customers,
    round(count(activity.customer_key)::numeric / offsets.cohort_size, 4) as retention_rate
from offsets
left join activity
    on
        offsets.cohort_month = activity.cohort_month
        and offsets.months_since_first_order = activity.months_since_first_order
group by offsets.cohort_month, offsets.months_since_first_order, offsets.cohort_size
