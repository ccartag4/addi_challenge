-- Business test (DMBOK: consistency). FIFO means money never reaches a later installment while
-- an earlier one is still unsettled (A21). Returns any loan where an installment is not fully
-- paid (full history) but a later installment of the same loan received something.
{{ config(meta = {'dq_dimension': 'consistency'}) }}

with s as (
    select loan_id, installment_number, due_date, amount_due, paid_amount_any
    from {{ ref('fct_installment_status') }}
)

select
    a.loan_id,
    a.installment_number    as unsettled_installment,
    a.amount_due            as unsettled_amount_due,
    a.paid_amount_any       as unsettled_paid,
    b.installment_number    as later_installment_with_money,
    b.paid_amount_any       as later_paid
from s a
join s b
  on  b.loan_id = a.loan_id
  and (b.due_date > a.due_date
       or (b.due_date = a.due_date and b.installment_number > a.installment_number))
where a.paid_amount_any < a.amount_due
  and b.paid_amount_any > 0
