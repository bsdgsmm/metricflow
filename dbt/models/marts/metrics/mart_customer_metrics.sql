with as_of as (
    select max(order_date) as as_of_date
    from {{ ref('fct_orders') }}
),

customers as (
    select * from {{ ref('dim_customers') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
    where is_completed_sale
),

customer_orders as (
    select
        orders.customer_key,
        count(*) as order_count,
        max(orders.order_date) as last_order_date,
        sum(orders.net_sales) as net_sales,
        sum(orders.net_revenue) as net_revenue,
        sum(orders.gross_profit) as gross_profit,
        sum(orders.net_revenue) filter (
            where orders.order_date < customers.first_order_date + 365
        ) as net_revenue_first_365d
    from orders
    inner join customers
        on orders.customer_key = customers.customer_key
    group by orders.customer_key
),

combined as (
    select
        customers.customer_key,
        customers.customer_id,
        customers.country,
        customers.city,
        customers.acquisition_channel,
        customers.is_marketing_opt_in,
        customers.signup_date,
        customers.first_order_date,
        customers.first_order_month,
        customer_orders.last_order_date,
        coalesce(customer_orders.order_count, 0) as order_count,
        coalesce(customer_orders.net_sales, 0) as net_sales,
        coalesce(customer_orders.net_revenue, 0) as lifetime_net_revenue,
        coalesce(customer_orders.gross_profit, 0) as lifetime_gross_profit,
        customer_orders.net_revenue_first_365d,
        customers.first_order_date + 365 <= as_of.as_of_date + 1 as has_full_first_year,
        as_of.as_of_date - customer_orders.last_order_date as days_since_last_order
    from customers
    cross join as_of
    left join customer_orders
        on customers.customer_key = customer_orders.customer_key
)

select
    customer_key,
    customer_id,
    country,
    city,
    acquisition_channel,
    is_marketing_opt_in,
    signup_date,
    first_order_date,
    first_order_month,
    last_order_date,
    order_count,
    order_count >= 2 as is_repeat_customer,
    case
        when order_count = 0 then 'no_orders'
        when order_count = 1 then 'one_time'
        when order_count <= 3 then 'repeat'
        else 'loyal'
    end as frequency_segment,
    case
        when order_count > 0
            then ntile(4) over (
                partition by order_count > 0
                order by lifetime_net_revenue
            )
    end as lifetime_value_quartile,
    lifetime_net_revenue,
    lifetime_gross_profit,
    round(net_sales / nullif(order_count, 0), 2) as average_order_value,
    case when has_full_first_year then net_revenue_first_365d end as net_revenue_first_365d,
    coalesce(has_full_first_year, false) as has_full_first_year,
    days_since_last_order
from combined
