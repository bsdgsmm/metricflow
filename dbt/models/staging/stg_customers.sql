with source as (
    select * from {{ source('raw', 'customers') }}
)

select
    customer_id,
    signup_date,
    trim(country) as country,
    trim(city) as city,
    lower(trim(acquisition_channel)) as acquisition_channel,
    marketing_opt_in as is_marketing_opt_in
from source
