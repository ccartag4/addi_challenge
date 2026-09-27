-- Gold / consumption. Grain: one row per valid loan, as of `snapshot_date` (README 4.1.2).
--
--   outstanding_local / outstanding_usd   sum of amount_due of every installment not settled as
--                                          of the date, overdue or not yet due (A11), converted
--                                          at the snapshot-date FX rate (A12)
--   outstanding_net_of_partial_*           secondary view: unsettled amount net of partial payments
--   dpd                                    days since the due date of the oldest unpaid
--                                          installment; 0 when nothing is overdue
--   dpd_bucket                             0 | 1-30 | 31-60 | 61-90 | 90+
--   is_par30                               dpd > 30 (numerator of PAR30)
--   loan_status                            SETTLED | CURRENT | DELINQUENT
--
-- Everything derives from fct_installment_status, so this mart never re-implements FIFO or
-- as-of logic; it aggregates and classifies.
{% set as_of_date = "cast('" ~ var('snapshot_date') ~ "' as date)" %}

with loans as (
    select
        loan_id, application_id, customer_id, person_sk, merchant_id, merchant_sk,
        merchant_category_at_disbursement, currency, principal, principal_usd,
        fx_units_per_usd as fx_units_per_usd_at_disbursement,
        disbursed_date, disbursed_month, term_months
    from {{ ref('fct_loan') }}
),

per_loan as (
    select
        loan_id,
        max(as_of_date)                                                         as as_of_date,
        count(*)                                                                as n_installments,
        count(*) filter (where is_settled)                                      as n_settled,
        count(*) filter (where is_partially_paid)                               as n_partial,
        count(*) filter (where paid_amount = 0)                                 as n_unpaid,
        count(*) filter (where is_due)                                          as n_due,
        count(*) filter (where is_overdue)                                      as n_overdue,
        count(*) filter (where not is_due)                                      as n_not_yet_due,
        sum(amount_due)                                                         as total_amount_due,
        sum(paid_amount)                                                        as paid_amount,
        coalesce(sum(amount_due)        filter (where not is_settled), 0)       as outstanding_local,
        coalesce(sum(remaining_amount)  filter (where not is_settled), 0)       as outstanding_net_of_partial_local,
        coalesce(sum(amount_due)        filter (where is_overdue), 0)           as overdue_amount_local,
        min(due_date) filter (where is_overdue)                                 as oldest_overdue_due_date,
        min(due_date) filter (where not is_settled and not is_due)              as next_due_date,
        max(last_payment_date)                                                  as last_payment_date,
        bool_or(is_fpd30_eligible)                                              as is_fpd30_eligible,
        bool_or(is_fpd30)                                                       as is_fpd30
    from {{ ref('fct_installment_status') }}
    group by loan_id
),

fx_snapshot as (
    select currency, units_per_usd
    from {{ ref('int_fx_daily') }}
    where rate_date = {{ as_of_date }}
),

measured as (
    select
        l.*,
        p.as_of_date,
        p.n_installments, p.n_settled, p.n_partial, p.n_unpaid,
        p.n_due, p.n_overdue, p.n_not_yet_due,
        p.total_amount_due,
        p.paid_amount,
        p.outstanding_local,
        p.outstanding_net_of_partial_local,
        p.overdue_amount_local,
        p.oldest_overdue_due_date,
        p.next_due_date,
        p.last_payment_date,
        case when p.oldest_overdue_due_date is null then 0
             else p.as_of_date - p.oldest_overdue_due_date end                  as dpd,
        fx.units_per_usd                                                        as fx_units_per_usd_at_snapshot,
        p.is_fpd30_eligible,
        p.is_fpd30
    from loans l
    join per_loan p using (loan_id)
    left join fx_snapshot fx on fx.currency = l.currency
)

select
    *,
    case
        when dpd = 0  then '0'
        when dpd <= 30 then '1-30'
        when dpd <= 60 then '31-60'
        when dpd <= 90 then '61-90'
        else               '90+'
    end                                                                         as dpd_bucket,
    (dpd > 30)                                                                  as is_par30,
    case
        when outstanding_local = 0 then 'SETTLED'
        when dpd > 0               then 'DELINQUENT'
        else                            'CURRENT'
    end                                                                         as loan_status,
    cast(outstanding_local / fx_units_per_usd_at_snapshot as decimal(18, 6))                as outstanding_usd,
    cast(outstanding_net_of_partial_local / fx_units_per_usd_at_snapshot as decimal(18, 6)) as outstanding_net_of_partial_usd,
    cast(overdue_amount_local / fx_units_per_usd_at_snapshot as decimal(18, 6))             as overdue_amount_usd,
    cast(outstanding_local / fx_units_per_usd_at_disbursement as decimal(18, 6))            as outstanding_usd_at_disbursement_rate,
    as_of_date - last_payment_date                                              as days_since_last_payment
from measured
