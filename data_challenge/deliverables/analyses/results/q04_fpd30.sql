-- Q4. Global FPD30, and FPD30 for the 2026-01 cohort (A23), as of snapshot_date.
-- Source: gold.dm_loan_delinquency_snapshot (flags computed in silver.fct_installment_status).
select
    scope,
    fpd30_eligible_loans,
    fpd30_loans,
    fpd30_unpaid,
    fpd30_paid_late,
    round(100.0 * fpd30_loans / fpd30_eligible_loans, 4)   as fpd30_pct
from (
    select
        'global' as scope,
        count(*) filter (where is_fpd30_eligible)                                   as fpd30_eligible_loans,
        count(*) filter (where is_fpd30)                                            as fpd30_loans,
        count(*) filter (where is_fpd30 and n_settled = 0 and n_partial = 0)        as fpd30_unpaid,
        count(*) filter (where is_fpd30 and (n_settled > 0 or n_partial > 0))       as fpd30_paid_late
    from {{ ref('dm_loan_delinquency_snapshot') }}
    union all
    select
        'cohort 2026-01',
        count(*) filter (where is_fpd30_eligible),
        count(*) filter (where is_fpd30),
        count(*) filter (where is_fpd30 and n_settled = 0 and n_partial = 0),
        count(*) filter (where is_fpd30 and (n_settled > 0 or n_partial > 0))
    from {{ ref('dm_loan_delinquency_snapshot') }}
    where disbursed_month = date '2026-01-01'
)
order by scope desc
