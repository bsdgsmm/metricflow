with source as (
    select * from {{ source('raw', 'orders') }}
)

select
    order_id,
    customer_id,
    order_timestamp as ordered_at,
    -- Reporting dates are defined in UTC so results do not depend on the session time zone.
    (order_timestamp at time zone 'UTC')::date as order_date,
    status as order_status,
    status = 'cancelled' as is_cancelled,
    channel as order_channel,
    payment_method
from source
