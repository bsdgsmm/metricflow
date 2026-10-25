-- The product version on each fact row must be the one valid on the order date.
select
    fct.order_item_id,
    fct.order_date,
    dim.valid_from,
    dim.valid_to
from {{ ref('fct_order_items') }} as fct
inner join {{ ref('dim_products') }} as dim
    on fct.product_key = dim.product_key
where
    fct.order_date < dim.valid_from
    or fct.order_date >= dim.valid_to
