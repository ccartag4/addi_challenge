-- Silver / core. Grain: loan_id x installment_number for every valid loan (130,297 rows).
-- State of each installment AS OF `snapshot_date` (A20): how much of it was paid, when it was
-- settled, and how many days past due it accrued. Columns suffixed _any use every effective
-- payment regardless of the cut, so month-end series can be derived later without re-running
-- the allocation.
--
--   paid_amount        FIFO-allocated money received on or before as_of_date (A21)
--   is_settled         paid_amount covers amount_due
--   settled_date       Bogotá date of the payment that completed the installment (A22)
--   days_to_settle     settled_date - due_date (negative = paid early)
--   days_past_due      accrued: until settlement if settled, until as_of_date otherwise (A23)
--   is_fpd30_eligible  first installment whose due date reached the 30-day mark by as_of_date
--   is_fpd30           eligible and more than 30 days past due (paid late or still unpaid)
{% set as_of_date = "cast('" ~ var('snapshot_date') ~ "' as date)" %}

with loans as (
    select loan_id, customer_id, person_sk, merchant_id, merchant_sk, currency,
           disbursed_date, disbursed_month, term_months
    from {{ ref('fct_loan') }}
),

installments as (
    select i.loan_id, i.installment_number, i.due_date, i.amount_due
    from {{ ref('stg_installments') }} i
    join loans using (loan_id)
),

alloc_as_of as (
    select
        loan_id,
        installment_number,
        sum(allocated_amount)   as paid_amount,
        min(paid_date)          as first_payment_date,
        max(paid_date)          as last_payment_date,
        count(*)                as n_payments_allocated
    from {{ ref('int_payment_allocation') }}
    where paid_date <= {{ as_of_date }}
    group by 1, 2
),

alloc_any as (
    select
        loan_id,
        installment_number,
        sum(allocated_amount)   as paid_amount_any,
        max(paid_date)          as last_payment_date_any
    from {{ ref('int_payment_allocation') }}
    group by 1, 2
),

base as (
    select
        i.loan_id,
        i.installment_number,
        i.due_date,
        i.amount_due,
        l.customer_id,
        l.person_sk,
        l.merchant_id,
        l.merchant_sk,
        l.currency,
        l.disbursed_date,
        l.disbursed_month,
        l.term_months,
        {{ as_of_date }}                                            as as_of_date,
        coalesce(a.paid_amount, 0)                                  as paid_amount,
        a.first_payment_date,
        a.last_payment_date,
        coalesce(a.n_payments_allocated, 0)                         as n_payments_allocated,
        coalesce(y.paid_amount_any, 0)                              as paid_amount_any,
        y.last_payment_date_any
    from installments i
    join loans l using (loan_id)
    left join alloc_as_of a using (loan_id, installment_number)
    left join alloc_any   y using (loan_id, installment_number)
),

derived as (
    select
        *,
        (installment_number = 1)                                    as is_first_installment,
        cast(date_trunc('month', due_date) as date)                 as due_month,
        amount_due - paid_amount                                    as remaining_amount,
        (paid_amount >= amount_due)                                 as is_settled,
        (paid_amount > 0 and paid_amount < amount_due)              as is_partially_paid,
        (due_date <= as_of_date)                                    as is_due,
        (paid_amount_any >= amount_due)                             as is_settled_any
    from base
),

dated as (
    select
        *,
        case when is_settled     then last_payment_date     end     as settled_date,
        case when is_settled_any then last_payment_date_any end     as settled_date_any,
        (is_due and not is_settled)                                 as is_overdue
    from derived
),

measured as (
    select
        *,
        case when is_settled then settled_date - due_date end       as days_to_settle,
        case
            when is_settled then greatest(0, settled_date - due_date)
            else                 greatest(0, as_of_date - due_date)
        end                                                         as days_past_due,
        (is_first_installment and due_date <= as_of_date - 30)      as is_fpd30_eligible
    from dated
)

select
    {{ dbt_utils.generate_surrogate_key(['loan_id', 'installment_number']) }} as installment_sk,
    loan_id,
    installment_number,
    due_date,
    due_month,
    amount_due,
    currency,
    customer_id,
    person_sk,
    merchant_id,
    merchant_sk,
    disbursed_date,
    disbursed_month,
    term_months,
    is_first_installment,
    as_of_date,
    paid_amount,
    remaining_amount,
    is_settled,
    is_partially_paid,
    is_due,
    is_overdue,
    settled_date,
    first_payment_date,
    last_payment_date,
    n_payments_allocated,
    days_to_settle,
    days_past_due,
    is_fpd30_eligible,
    (is_fpd30_eligible and days_past_due > 30)                      as is_fpd30,
    paid_amount_any,
    is_settled_any,
    settled_date_any
from measured
