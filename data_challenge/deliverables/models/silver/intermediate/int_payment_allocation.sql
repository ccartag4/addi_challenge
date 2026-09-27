-- Silver / intermediate. Grain: one row per (payment, installment) pair that the payment
-- funds, i.e. the FIFO allocation of loan-level payments to the installment plan (A21).
--
-- Method (no recursion, pure window functions):
--   * installments of a loan, ordered by due_date, form consecutive intervals on a "debt line":
--       [cum_due_start, cum_due_end)   where cum_due_end = running sum of amount_due
--   * effective payments of the loan, ordered by paid_at_utc, form consecutive intervals on a
--     "money line":
--       [cum_paid_start, cum_paid_end) where cum_paid_end = running sum of amount (fct_payment)
--   * a payment funds an installment by the length of the overlap of the two intervals.
--   The oldest payment therefore settles the oldest installment first, one payment can cover
--   several installments and one installment can need several payments. Money beyond the
--   total plan (overpayment) overlaps no installment and is simply not allocated.
--
-- Full history: every effective payment is allocated regardless of the snapshot date;
-- fct_installment_status applies the as-of cut by paid_date (A20).
with installments as (
    select
        i.loan_id,
        i.installment_number,
        i.due_date,
        i.amount_due,
        sum(i.amount_due) over (
            partition by i.loan_id
            order by i.due_date, i.installment_number
            rows between unbounded preceding and current row
        )                                                   as cum_due_end
    from {{ ref('stg_installments') }} i
    join {{ ref('fct_loan') }} l using (loan_id)            -- valid loans only (A5)
),

debt_line as (
    select *, cum_due_end - amount_due as cum_due_start
    from installments
),

money_line as (
    select
        loan_id,
        payment_id,
        loan_payment_seq                                    as payment_seq,
        paid_at_utc,
        paid_date,
        amount                                              as payment_amount,
        loan_cumulative_paid                                as cum_paid_end,
        loan_cumulative_paid - amount                       as cum_paid_start
    from {{ ref('fct_payment') }}
)

select
    p.loan_id,
    p.payment_id,
    i.installment_number,
    p.payment_seq,
    p.paid_at_utc,
    p.paid_date,
    i.due_date,
    least(p.cum_paid_end, i.cum_due_end)
        - greatest(p.cum_paid_start, i.cum_due_start)       as allocated_amount,
    p.payment_amount,
    i.amount_due,
    p.cum_paid_start,
    p.cum_paid_end,
    i.cum_due_start,
    i.cum_due_end
from money_line p
join debt_line i
  on  i.loan_id        = p.loan_id
  and p.cum_paid_start < i.cum_due_end
  and p.cum_paid_end   > i.cum_due_start
