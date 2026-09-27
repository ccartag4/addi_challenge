-- Silver / core. Grain: one row per effective payment (A9): SETTLED, not voided by any
-- reversal, on a valid loan (A5). Amounts are in major units for both source systems (A8);
-- the loan reference is normalized (F10). amount_usd uses the FX rate of the Bogotá payment
-- date (A7) for reporting; allocation to installments (FIFO) works in local currency.
-- loan_payment_seq and loan_cumulative_paid order the payments inside each loan, which is the
-- basis of the FIFO allocation in int_installment_allocation.
with effective as (
    select *
    from {{ ref('int_payment_classified') }}
    where payment_class = 'EFFECTIVE'
      and loan_is_valid
),

fx as (
    select rate_date, currency, units_per_usd
    from {{ ref('int_fx_daily') }}
),

loans as (
    select loan_id, customer_id, person_sk, merchant_id, currency
    from {{ ref('fct_loan') }}
)

select
    e.payment_id,
    e.loan_id,
    l.customer_id,
    l.person_sk,
    l.merchant_id,
    e.paid_at_utc,
    e.paid_date,
    cast(date_trunc('month', e.paid_date) as date)              as paid_month,
    e.amount,
    l.currency,
    fx.units_per_usd                                            as fx_units_per_usd,
    cast(e.amount / fx.units_per_usd as decimal(18, 6))         as amount_usd,
    e.source_system,
    e.payment_method,
    e.loan_ref,
    row_number() over (
        partition by e.loan_id order by e.paid_at_utc, e.payment_id
    )                                                           as loan_payment_seq,
    sum(e.amount) over (
        partition by e.loan_id order by e.paid_at_utc, e.payment_id
        rows between unbounded preceding and current row
    )                                                           as loan_cumulative_paid
from effective e
join loans l using (loan_id)
left join fx
       on fx.currency  = l.currency
      and fx.rate_date = e.paid_date
