-- Business test (DMBOK: accuracy). Neither a voided payment nor a reversal row may count as
-- money received (A9, F11). Returns any fct_payment row that is the target of a REVERSED row
-- in staging, or is itself a reversal.
{{ config(meta = {'dq_dimension': 'accuracy'}) }}

select
    f.payment_id,
    'target_of_reversal' as problem
from {{ ref('fct_payment') }} f
where exists (
    select 1
    from {{ ref('stg_payments') }} r
    where r.is_reversal
      and r.reversed_payment_id = f.payment_id
)

union all

select
    f.payment_id,
    'is_reversal_row' as problem
from {{ ref('fct_payment') }} f
join {{ ref('stg_payments') }} s using (payment_id)
where s.is_reversal
