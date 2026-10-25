with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

product_versions as (
    select * from {{ ref('int_product_versions') }}
),

returns_by_line as (
    select
        order_item_id,
        sum(returned_quantity) as returned_quantity,
        sum(refund_amount) as refund_amount,
        min(returned_on) as first_returned_on
    from {{ ref('stg_returns') }}
    group by order_item_id
),

joined as (
    select
        order_items.order_item_id,
        order_items.order_id,
        orders.customer_id,
        order_items.product_id,
        product_versions.product_key,
        orders.ordered_at,
        orders.order_date,
        orders.is_cancelled,
        order_items.quantity,
        order_items.unit_price,
        product_versions.unit_cost,
        order_items.gross_amount as gross_revenue,
        order_items.discount_amount,
        coalesce(returns_by_line.returned_quantity, 0) as returned_quantity,
        coalesce(returns_by_line.refund_amount, 0)::numeric(12, 2) as refund_amount,
        returns_by_line.first_returned_on
    from order_items
    inner join orders
        on order_items.order_id = orders.order_id
    left join product_versions
        on
            order_items.product_id = product_versions.product_id
            and orders.order_date >= product_versions.valid_from
            and (
                orders.order_date < product_versions.valid_to
                or product_versions.valid_to is null
            )
    left join returns_by_line
        on order_items.order_item_id = returns_by_line.order_item_id
)

select
    order_item_id,
    order_id,
    customer_id,
    product_id,
    product_key,
    ordered_at,
    order_date,
    is_cancelled,
    quantity,
    returned_quantity,
    returned_quantity > 0 as has_return,
    first_returned_on,
    unit_price,
    unit_cost,
    gross_revenue,
    discount_amount,
    gross_revenue - discount_amount as net_sales,
    refund_amount,
    gross_revenue - discount_amount - refund_amount as net_revenue,
    -- Returned units are assumed to be restocked, so their cost is not recognised.
    (quantity - returned_quantity) * unit_cost as cost_of_goods_sold,
    gross_revenue
    - discount_amount
    - refund_amount
    - (quantity - returned_quantity) * unit_cost as gross_profit
from joined
