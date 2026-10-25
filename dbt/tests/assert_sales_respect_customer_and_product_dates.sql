-- Orders cannot precede the customer's signup or the product's launch, and products cannot be
-- sold on or after their discontinuation date.
select
    items.order_item_id,
    items.order_date,
    customers.signup_date,
    products.launched_on,
    products.discontinued_on
from {{ ref('fct_order_items') }} as items
inner join {{ ref('dim_customers') }} as customers
    on items.customer_key = customers.customer_key
inner join {{ ref('dim_products') }} as products
    on items.product_key = products.product_key
where
    items.order_date < customers.signup_date
    or items.order_date < products.launched_on
    or items.order_date >= products.discontinued_on
