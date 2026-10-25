-- SCD Type 2 validity: two versions of the same product must never be valid on the same day.
select
    earlier.product_id,
    earlier.product_key as earlier_key,
    later.product_key as later_key
from {{ ref('dim_products') }} as earlier
inner join {{ ref('dim_products') }} as later
    on
        earlier.product_id = later.product_id
        and earlier.product_key != later.product_key
        and earlier.valid_from <= later.valid_from
        and (earlier.valid_to is null or earlier.valid_to > later.valid_from)
