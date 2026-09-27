-- Silver / staging. Grain: rate_date x currency as published (business days only, F12).
-- The forward-filled daily calendar (A7) is built in int_fx_daily.
with src as (
    select * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_fx_rates') }}
)

select distinct
    cast(rate_date as date)                             as rate_date,
    upper(trim(currency))                               as currency,
    try_cast(units_per_usd as decimal(18, 6))           as units_per_usd
from src
