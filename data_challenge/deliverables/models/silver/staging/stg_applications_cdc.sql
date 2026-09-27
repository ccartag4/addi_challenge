-- Silver / staging. Grain: one CDC event, typed, exact duplicates removed (F1, F2).
-- No business filtering here: deleted applications and placeholder customers are kept and
-- flagged, so the intermediate layer applies rules A2, A3 and A4 explicitly and testably.
with src as (
    select * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_applications_cdc') }}
),

typed as (
    select distinct
        cast(application_id as bigint)                  as application_id,
        cast(customer_id as bigint)                     as customer_id_raw,
        cast(merchant_id as bigint)                     as merchant_id,
        {{ parse_number('requested_amount') }}          as requested_amount,
        upper(trim(currency))                           as currency,
        upper(trim(status))                             as status,
        {{ parse_number('approved_amount') }}           as approved_amount,
        {{ parse_utc_ts('event_at_utc') }}              as event_at_utc,
        {{ parse_utc_ts('_ingested_at_utc') }}          as ingested_at_utc,
        upper(trim(_op))                                as cdc_op
    from src
)

select
    application_id,
    -- A4: the origination core writes a placeholder id when the customer is unknown
    case when customer_id_raw = {{ var('placeholder_customer_id') }} then null
         else customer_id_raw end                       as customer_id,
    customer_id_raw = {{ var('placeholder_customer_id') }} as is_placeholder_customer,
    merchant_id,
    requested_amount,
    currency,
    status,
    approved_amount,
    event_at_utc,
    {{ to_business_date('event_at_utc') }}              as event_date,
    ingested_at_utc,
    cdc_op,
    -- ordering helper for A2: at identical instants an insert precedes an update precedes a delete
    case cdc_op when 'I' then 1 when 'U' then 2 when 'D' then 3 end as cdc_op_rank
from typed
