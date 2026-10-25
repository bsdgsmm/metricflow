with customers as (
    select * from {{ ref('stg_customers') }}
),

first_orders as (
    select
        customer_id,
        min(order_date) as first_order_date
    from {{ ref('int_customer_order_sequence') }}
    group by customer_id
)

select
    md5(customers.customer_id) as customer_key,
    customers.customer_id,
    customers.signup_date,
    date_trunc('month', customers.signup_date)::date as signup_month,
    customers.country,
    customers.city,
    customers.acquisition_channel,
    customers.is_marketing_opt_in,
    first_orders.first_order_date,
    date_trunc('month', first_orders.first_order_date)::date as first_order_month,
    first_orders.first_order_date is not null as has_ordered
from customers
left join first_orders
    on customers.customer_id = first_orders.customer_id
