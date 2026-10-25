with source as (
    select * from {{ source('raw', 'product_price_history') }}
)

select
    product_id,
    valid_from,
    list_price,
    unit_cost
from source
