-- Load history per table: how many rows each run inserted, updated or rejected.
select
    batch_id,
    table_name,
    status,
    rows_read,
    rows_inserted,
    rows_updated,
    rows_unchanged,
    rows_rejected,
    duplicates_removed,
    finished_at - started_at as duration,
    error_message
from raw.ingestion_runs
order by started_at desc, table_name asc;
