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
    -- unpaid / paid late refer to the FIRST installment (the one FPD30 is about)
    select
        'global' as scope,
        count(*) filter (where d.is_fpd30_eligible)                                 as fpd30_eligible_loans,
        count(*) filter (where d.is_fpd30)                                          as fpd30_loans,
        count(*) filter (where d.is_fpd30 and not f.is_settled)                     as fpd30_unpaid,
        count(*) filter (where d.is_fpd30 and f.is_settled)                         as fpd30_paid_late
    from {{ ref('dm_loan_delinquency_snapshot') }} d
    join {{ ref('fct_installment_status') }} f
      on f.loan_id = d.loan_id and f.installment_number = 1
    union all
    select
        'cohort 2026-01',
        count(*) filter (where d.is_fpd30_eligible),
        count(*) filter (where d.is_fpd30),
        count(*) filter (where d.is_fpd30 and not f.is_settled),
        count(*) filter (where d.is_fpd30 and f.is_settled)
    from {{ ref('dm_loan_delinquency_snapshot') }} d
    join {{ ref('fct_installment_status') }} f
      on f.loan_id = d.loan_id and f.installment_number = 1
    where d.disbursed_month = date '2026-01-01'
)
order by scope desc
