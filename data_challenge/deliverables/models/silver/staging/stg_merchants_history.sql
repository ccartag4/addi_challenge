-- Silver / staging. Grain: one merchant attribute version (merchant_id x valid_from), typed.
-- The SCD2 end dates and current flag are derived in dim_merchant.
with src as (
    select * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_merchants_history') }}
)

select distinct
    cast(merchant_id as bigint)                         as merchant_id,
    {{ clean_text('merchant_name') }}                   as merchant_name,
    {{ normalize_key('merchant_name') }}                as merchant_name_key,   -- F15: casing variants
    upper(trim(category))                               as category,
    upper(trim(country))                                as country,
    cast(valid_from as date)                            as valid_from
from src
