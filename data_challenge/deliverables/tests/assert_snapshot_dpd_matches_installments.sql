-- Business test (DMBOK: accuracy). Gold must agree with silver: a loan's DPD in the snapshot
-- equals as_of_date minus the due date of its oldest overdue installment (README 4.2), and its
-- outstanding balance equals the sum of its unsettled installments (A11). Recomputed here
-- straight from fct_installment_status, independently of the mart's own aggregation.
{{ config(meta = {'dq_dimension': 'accuracy'}) }}

with recomputed as (
    select
        loan_id,
        coalesce(max(as_of_date - due_date) filter (where is_overdue), 0)   as dpd_recomputed,
        coalesce(sum(amount_due) filter (where not is_settled), 0)          as outstanding_recomputed
    from {{ ref('fct_installment_status') }}
    group by loan_id
)

select
    d.loan_id,
    d.dpd,
    r.dpd_recomputed,
    d.outstanding_local,
    r.outstanding_recomputed
from {{ ref('dm_loan_delinquency_snapshot') }} d
join recomputed r using (loan_id)
where d.dpd <> r.dpd_recomputed
   or abs(d.outstanding_local - r.outstanding_recomputed) > 0.005
