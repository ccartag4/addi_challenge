-- Business test (DMBOK: consistency). The arithmetic of A9 must hold exactly:
--   effective payments = SETTLED rows - distinct voided payments
-- and every effective payment on a valid loan is in fct_payment. A payment reversed twice
-- (F11) must be subtracted once, not twice. Returns one row when the counts disagree.
{{ config(meta = {'dq_dimension': 'consistency'}) }}

with counts as (
    select
        (select count(*) from {{ ref('stg_payments') }} where status = 'SETTLED')                       as settled_rows,
        (select count(distinct reversed_payment_id) from {{ ref('stg_payments') }} where is_reversal)  as voided_payments,
        (select count(*) from {{ ref('int_payment_classified') }} where payment_class = 'EFFECTIVE')  as effective_all_loans,
        (select count(*) from {{ ref('int_payment_classified') }}
          where payment_class = 'EFFECTIVE' and loan_is_valid)                                          as effective_valid_loans,
        (select count(*) from {{ ref('fct_payment') }})                                                 as fct_rows
)

select *
from counts
where effective_all_loans   <> settled_rows - voided_payments
   or fct_rows              <> effective_valid_loans
