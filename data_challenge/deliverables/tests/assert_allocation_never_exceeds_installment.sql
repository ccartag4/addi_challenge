-- Business test (DMBOK: accuracy). No installment receives more money than it is due (A21):
-- the overlap construction caps allocations at the installment interval. Tolerance 0.005.
{{ config(meta = {'dq_dimension': 'accuracy'}) }}

with allocated as (
    select loan_id, installment_number, sum(allocated_amount) as allocated
    from {{ ref('int_payment_allocation') }}
    group by loan_id, installment_number
)

select
    i.loan_id,
    i.installment_number,
    i.amount_due,
    a.allocated
from {{ ref('stg_installments') }} i
join allocated a using (loan_id, installment_number)
where a.allocated > i.amount_due + 0.005
