-- Business test (DMBOK: accuracy). FIFO allocation conserves money: the amount a payment funds
-- across installments can never exceed the payment itself (A21). Tolerance 0.005 for decimal
-- rounding.
{{ config(meta = {'dq_dimension': 'accuracy'}) }}

with allocated as (
    select payment_id, sum(allocated_amount) as allocated
    from {{ ref('int_payment_allocation') }}
    group by payment_id
)

select
    p.payment_id,
    p.loan_id,
    p.amount,
    a.allocated
from {{ ref('fct_payment') }} p
join allocated a using (payment_id)
where a.allocated > p.amount + 0.005
