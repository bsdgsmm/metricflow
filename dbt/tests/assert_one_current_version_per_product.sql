-- Every product must have exactly one open-ended version, and it must be the latest one.
with versions as (
    select
        product_id,
        count(*) filter (where is_current) as current_versions,
        max(version_number) as latest_version,
        max(version_number) filter (where is_current) as current_version
    from {{ ref('dim_products') }}
    group by product_id
)

select *
from versions
where current_versions != 1 or current_version != latest_version
