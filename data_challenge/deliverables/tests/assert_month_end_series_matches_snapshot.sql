-- Business test (DMBOK: consistency). Two independent computations of the same state must
-- agree: the month-end series (built from settled_date_any and a month spine) at
-- month_end = snapshot_date, and the delinquency snapshot (built from the as-of installment
-- status). Same loans, same DPD, same balance to the cent. This is what lets the monthly PAR30
-- in agg_merchant_monthly be trusted (A13).
{{ config(meta = {'dq_dimension': 'consistency'}) }}

with series as (
    select loan_id, dpd, outstanding_local, outstanding_usd
    from {{ ref('int_loan_month_end_status') }}
    where month_end = cast('{{ var("snapshot_date") }}' as date)
),

snapshot as (
    select loan_id, dpd, outstanding_local, outstanding_usd
    from {{ ref('dm_loan_delinquency_snapshot') }}
)

select
    coalesce(a.loan_id, b.loan_id)  as loan_id,
    a.dpd                           as series_dpd,
    b.dpd                           as snapshot_dpd,
    a.outstanding_local             as series_outstanding,
    b.outstanding_local             as snapshot_outstanding,
    case
        when a.loan_id is null then 'missing_in_series'
        when b.loan_id is null then 'missing_in_snapshot'
        when a.dpd <> b.dpd then 'dpd_differs'
        else 'balance_differs'
    end                             as problem
from series a
full outer join snapshot b using (loan_id)
where a.loan_id is null
   or b.loan_id is null
   or a.dpd <> b.dpd
   or abs(a.outstanding_local - b.outstanding_local) > 0.005
   or abs(a.outstanding_usd - b.outstanding_usd) > 0.01
