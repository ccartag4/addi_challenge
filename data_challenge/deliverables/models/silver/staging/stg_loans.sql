-- Silver / staging. Grain: one loan as delivered, typed. Validity against the application
-- (A5) is decided in the intermediate layer, not here.
with src as (
    select * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_loans') }}
),

typed as (
    select distinct
        cast(loan_id as bigint)                         as loan_id,
        cast(application_id as bigint)                  as application_id,
        cast(customer_id as bigint)                     as customer_id,
        cast(merchant_id as bigint)                     as merchant_id,
        {{ parse_number('principal') }}                 as principal,
        upper(trim(currency))                           as currency,
        cast(term_months as integer)                    as term_months,
        try_cast(apr as decimal(9, 6))                  as apr,
        {{ parse_utc_ts('disbursed_at_utc') }}          as disbursed_at_utc,
        upper(trim(status))                             as status
    from src
),

dated as (
    select
        *,
        {{ to_business_date('disbursed_at_utc') }}      as disbursed_date   -- A6
    from typed
)

select
    *,
    cast(date_trunc('month', disbursed_date) as date)   as disbursed_month
from dated
