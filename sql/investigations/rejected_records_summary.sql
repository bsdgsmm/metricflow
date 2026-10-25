-- Rows rejected by the latest ingestion run of each source file, grouped by reason.
select
    table_name,
    reason,
    count(*) as rejected_rows,
    min(source_row_number) as first_row,
    max(source_row_number) as last_row,
    min(detail) as example_detail
from raw.rejected_records
group by table_name, reason
order by table_name asc, rejected_rows desc;
