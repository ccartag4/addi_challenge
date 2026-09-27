-- Silver / staging. Grain: one payment row per payment_id (SETTLED and REVERSED alike).
-- Normalizes the two source systems (F9, F10) and collapses the rows that differ only by
-- timestamp format (F3, A10): after parsing, DISTINCT makes them one row.
-- Reversal semantics (A9) are applied in the intermediate layer.
with src as (
    select * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_payments') }}
),

typed as (
    select distinct
        cast(payment_id as bigint)                                  as payment_id,
        loan_ref,
        cast(regexp_extract(loan_ref, '(\d+)$', 1) as bigint)       as loan_id,      -- F10
        {{ parse_utc_ts('paid_at_utc') }}                           as paid_at_utc,
        {{ parse_number('amount_raw', 18, 4) }}                     as amount_raw,
        lower(trim(source_system))                                  as source_system,
        upper(trim(payment_method))                                 as payment_method,
        upper(trim(status))                                         as status,
        cast(reversed_payment_id as bigint)                         as reversed_payment_id
    from src
)

select
    payment_id,
    loan_id,
    loan_ref,
    paid_at_utc,
    {{ to_business_date('paid_at_utc') }}                           as paid_date,     -- A6
    amount_raw,
    -- A8 / F9: legacy_v1 reports minor units for both currencies
    cast(case when source_system = 'legacy_v1' then amount_raw / 100
              else amount_raw end as decimal(18, 2))                as amount,
    source_system,
    payment_method,
    status,
    status = 'REVERSED'                                             as is_reversal,
    reversed_payment_id
from typed
