-- DQ profiling 01 — Validity: which date/timestamp formats does each column actually contain?
-- Digits are replaced by 9 so every distinct *shape* is counted once.
with cols as (
    select 'applications_cdc.event_at_utc'     as col, event_at_utc     as v from {{ ref('brz_applications_cdc') }}
    union all
    select 'applications_cdc._ingested_at_utc' as col, _ingested_at_utc as v from {{ ref('brz_applications_cdc') }}
    union all
    select 'loans.disbursed_at_utc'            as col, disbursed_at_utc as v from {{ ref('brz_loans') }}
    union all
    select 'payments.paid_at_utc'              as col, paid_at_utc      as v from {{ ref('brz_payments') }}
    union all
    select 'customers.created_at'              as col, created_at       as v from {{ ref('brz_customers') }}
    union all
    select 'customers._ingested_at'            as col, _ingested_at     as v from {{ ref('brz_customers') }}
    union all
    select 'installments.due_date'             as col, due_date         as v from {{ ref('brz_installments') }}
    union all
    select 'merchants_history.valid_from'      as col, valid_from       as v from {{ ref('brz_merchants_history') }}
    union all
    select 'fx_rates.rate_date'                as col, rate_date        as v from {{ ref('brz_fx_rates') }}
)
select
    col,
    regexp_replace(v, '\d', '9', 'g') as shape,
    count(*)                          as n_rows,
    min(v)                            as example
from cols
group by 1, 2
order by 1, 3 desc
