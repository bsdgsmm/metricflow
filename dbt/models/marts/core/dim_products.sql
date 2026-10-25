select
    product_key,
    product_id,
    version_number,
    valid_from,
    valid_to,
    is_current,
    product_name,
    category,
    subcategory,
    brand,
    list_price,
    unit_cost,
    list_price - unit_cost as unit_margin,
    launched_on,
    discontinued_on,
    is_active
from {{ ref('int_product_versions') }}
