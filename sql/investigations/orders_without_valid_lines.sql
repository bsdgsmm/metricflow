-- Orders that exist without any valid order line, with the rejected lines that explain why.
select
    orders.order_id,
    orders.order_status,
    rejected.source_row_number,
    rejected.reason,
    rejected.detail
from marts.fct_orders as orders
left join raw.rejected_records as rejected
    on
        rejected.table_name = 'order_items'
        and rejected.payload ->> 'order_id' = orders.order_id
where orders.line_count = 0
order by orders.order_id, rejected.source_row_number;
