with prices as (
    select * from {{ ref('stg_product_prices') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

versioned as (
    select
        product_id,
        valid_from,
        -- valid_to is exclusive: a version applies while valid_from <= date < valid_to.
        lead(valid_from) over (
            partition by product_id
            order by valid_from
        ) as valid_to,
        row_number() over (
            partition by product_id
            order by valid_from
        ) as version_number,
        list_price,
        unit_cost
    from prices
)

select
    md5(versioned.product_id || '|' || versioned.valid_from::text) as product_key,
    versioned.product_id,
    versioned.version_number,
    versioned.valid_from,
    versioned.valid_to,
    versioned.valid_to is null as is_current,
    versioned.list_price,
    versioned.unit_cost,
    products.product_name,
    products.category,
    products.subcategory,
    products.brand,
    products.launched_on,
    products.discontinued_on,
    products.is_active
from versioned
inner join products
    on versioned.product_id = products.product_id
