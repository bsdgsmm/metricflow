with source as (
    select * from {{ source('raw', 'products') }}
)

select
    product_id,
    trim(product_name) as product_name,
    trim(category) as category,
    trim(subcategory) as subcategory,
    trim(brand) as brand,
    launched_on,
    discontinued_on,
    discontinued_on is null as is_active
from source
