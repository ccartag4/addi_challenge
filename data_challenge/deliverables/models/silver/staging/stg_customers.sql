-- Silver / staging. Grain: one row per customer_id (the technical key). The person grain
-- (A1) is built in dim_customer. Sentinels follow A16, creation date follows A15.
with src as (
    select * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_customers') }}
),

typed as (
    select distinct
        cast(customer_id as bigint)                     as customer_id,
        trim(document_number)                           as document_number,
        upper(trim(country))                            as country,
        {{ clean_text('city') }}                        as city_raw,
        {{ normalize_key('city') }}                     as city_key,
        lower({{ clean_text('email') }})                as email,
        try_cast(birth_year as integer)                 as birth_year_raw,
        {{ parse_number('monthly_income') }}            as monthly_income_raw,
        {{ parse_utc_ts('created_at') }}                as created_at_utc,
        {{ parse_utc_ts('_ingested_at') }}              as ingested_at_utc
    from src
)

select
    customer_id,
    document_number,
    country,
    city_raw,
    city_key,
    email,
    case when birth_year_raw <= 1900 then null else birth_year_raw end          as birth_year,      -- A16
    case when monthly_income_raw < 0 then null else monthly_income_raw end      as monthly_income,  -- A16
    created_at_utc,
    cast(created_at_utc as date)                                                as created_date,    -- A15
    ingested_at_utc
from typed
