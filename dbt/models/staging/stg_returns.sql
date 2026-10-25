with source as (
    select * from {{ source('raw', 'returns') }}
)

select
    return_id,
    order_item_id,
    return_date as returned_on,
    quantity as returned_quantity,
    refund_amount,
    reason as return_reason
from source
