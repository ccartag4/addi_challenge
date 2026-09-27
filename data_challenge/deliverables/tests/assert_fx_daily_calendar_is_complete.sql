-- Business test (DMBOK: completeness). The forward-filled FX calendar must have one row for
-- every day between its bounds, per currency; a hole would make a disbursement lose its USD
-- value silently (7,607 loans were disbursed on weekends, F12).
{{ config(meta = {'dq_dimension': 'completeness'}) }}

with per_currency as (
    select
        currency,
        count(*)                                        as n_rows,
        max(rate_date) - min(rate_date) + 1             as n_days_expected,
        count(distinct rate_date)                       as n_distinct_days
    from {{ ref('int_fx_daily') }}
    group by currency
)

select *
from per_currency
where n_rows <> n_days_expected
   or n_distinct_days <> n_days_expected
