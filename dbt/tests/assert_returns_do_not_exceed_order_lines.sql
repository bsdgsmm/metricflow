-- A line can never be refunded for more units or money than was sold, or before it was ordered.
select
    order_item_id,
    quantity,
    returned_quantity,
    net_sales,
    refund_amount,
    order_date,
    first_returned_on
from {{ ref('fct_order_items') }}
where
    returned_quantity > quantity
    or refund_amount > net_sales
    or first_returned_on < order_date
