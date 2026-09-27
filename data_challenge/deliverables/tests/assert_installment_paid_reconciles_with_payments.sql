-- Business test (DMBOK: consistency). Per loan, the money allocated to installments must equal
-- the money received, capped at the plan total (anything above the plan is overpayment and
-- stays unallocated by design, A21). Tolerance 0.01 per loan.
{{ config(meta = {'dq_dimension': 'consistency'}) }}

with paid as (
    select loan_id, sum(amount) as total_paid
    from {{ ref('fct_payment') }}
    group by loan_id
),

allocated as (
    select loan_id, sum(paid_amount_any) as total_allocated, sum(amount_due) as total_due
    from {{ ref('fct_installment_status') }}
    group by loan_id
)

select
    l.loan_id,
    coalesce(p.total_paid, 0)   as total_paid,
    a.total_due,
    a.total_allocated,
    least(coalesce(p.total_paid, 0), a.total_due) - a.total_allocated as difference
from {{ ref('fct_loan') }} l
join allocated a using (loan_id)
left join paid p using (loan_id)
where abs(least(coalesce(p.total_paid, 0), a.total_due) - a.total_allocated) > 0.01
