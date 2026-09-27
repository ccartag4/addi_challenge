-- DQ profiling 09 — Validity / Accuracy: does parse_utc_ts() cover every raw value, and how
-- many business dates move when UTC is converted to America/Bogota (assumption A6)?
-- Run after the macros exist (step 07).
with cols as (
    select 'applications_cdc.event_at_utc' as col, event_at_utc     as raw from {{ ref('brz_applications_cdc') }}
    union all
    select 'loans.disbursed_at_utc',              disbursed_at_utc as raw from {{ ref('brz_loans') }}
    union all
    select 'payments.paid_at_utc',                paid_at_utc      as raw from {{ ref('brz_payments') }}
    union all
    select 'customers.created_at',                created_at       as raw from {{ ref('brz_customers') }}
),
parsed as (
    select
        col,
        raw,
        {{ parse_utc_ts('raw') }}                       as ts_utc,
        {{ to_business_date(parse_utc_ts('raw')) }}     as d_bog,
        cast({{ parse_utc_ts('raw') }} as date)         as d_utc
    from cols
)
select
    col,
    count(*)                                                        as n_rows,
    count(raw)                                                      as raw_not_null,
    count(ts_utc)                                                   as parsed_not_null,
    count(raw) - count(ts_utc)                                      as parse_failures,
    min(ts_utc)                                                     as min_ts_utc,
    max(ts_utc)                                                     as max_ts_utc,
    sum(case when d_bog <> d_utc then 1 else 0 end)                 as rows_day_shifts_in_bogota,
    sum(case when date_trunc('month', d_bog) <> date_trunc('month', d_utc) then 1 else 0 end)
                                                                    as rows_month_shifts_in_bogota
from parsed
group by col
order by col
