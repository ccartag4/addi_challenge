-- Silver / intermediate. Grain: one row per payment_id from staging (110,136), classified:
--   EFFECTIVE      SETTLED and not referenced by any REVERSED row: money received (A9)
--   REVERSED_OUT   SETTLED but voided by one or more REVERSED rows: not money received
--   REVERSAL_ROW   the REVERSED row itself: never money received
-- Nothing is dropped here; fct_payment keeps only EFFECTIVE rows on valid loans.
with payments as (
    select * from {{ ref('stg_payments') }}
),

reversals as (
    -- one row per voided payment, however many reversal rows point at it (F11: 5 have two)
    select
        reversed_payment_id                 as payment_id,
        count(*)                            as n_reversal_rows,
        min(paid_at_utc)                    as first_reversed_at_utc,
        sum(amount)                         as reversal_amount_total
    from payments
    where is_reversal
    group by reversed_payment_id
),

loans as (
    select loan_id, is_valid as loan_is_valid, exclusion_reason as loan_exclusion_reason,
           currency as loan_currency, disbursed_at_utc
    from {{ ref('int_loan_validated') }}
)

select
    p.*,
    l.loan_is_valid,
    l.loan_exclusion_reason,
    l.loan_currency,
    l.disbursed_at_utc                                          as loan_disbursed_at_utc,
    r.n_reversal_rows,
    r.first_reversed_at_utc,
    r.reversal_amount_total,
    case
        when p.is_reversal                  then 'REVERSAL_ROW'
        when r.payment_id is not null       then 'REVERSED_OUT'
        else                                     'EFFECTIVE'
    end                                                         as payment_class,
    (l.loan_id is null)                                         as loan_missing
from payments p
left join reversals r on r.payment_id = p.payment_id
left join loans     l on l.loan_id    = p.loan_id
