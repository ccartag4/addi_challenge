-- Silver / intermediate. Grain: one row per valid loan x month end, from the loan's
-- disbursement month to the snapshot month (A13). The state of the loan at each month end:
-- outstanding balance (A11), DPD (A24), PAR30 flag, in local currency and USD at that month
-- end's FX rate (A12).
--
-- Why it is cheap: FIFO settlement dates do not depend on the reporting date, so
-- fct_installment_status.settled_date_any is enough to know whether an installment was
-- settled by any month end. No re-allocation is needed.
-- Consistency: at month_end = snapshot_date this model reproduces dm_loan_delinquency_snapshot
-- loan by loan (singular test assert_month_end_series_matches_snapshot).
{% set as_of_date = "cast('" ~ var('snapshot_date') ~ "' as date)" %}

with loans as (
    select loan_id, merchant_id, currency, disbursed_date
    from {{ ref('fct_loan') }}
),

bounds as (
    select
        cast(date_trunc('month', min(disbursed_date)) as date)      as first_month,
        cast(date_trunc('month', {{ as_of_date }}) as date)         as last_month
    from loans
),

month_series as (
    select cast(unnest(generate_series(first_month, last_month, interval 1 month)) as date) as month
    from bounds
),

month_ends as (
    select month, cast(last_day(month) as date) as month_end
    from month_series
    where last_day(month) <= {{ as_of_date }}
),

loan_months as (
    select l.loan_id, l.merchant_id, l.currency, l.disbursed_date, m.month, m.month_end
    from loans l
    join month_ends m on m.month_end >= l.disbursed_date
),

installments as (
    select loan_id, due_date, amount_due, settled_date_any
    from {{ ref('fct_installment_status') }}
),

state as (
    select
        lm.loan_id,
        lm.merchant_id,
        lm.currency,
        lm.disbursed_date,
        lm.month,
        lm.month_end,
        coalesce(sum(i.amount_due) filter (
            where i.settled_date_any is null or i.settled_date_any > lm.month_end), 0)      as outstanding_local,
        min(i.due_date) filter (
            where (i.settled_date_any is null or i.settled_date_any > lm.month_end)
              and i.due_date < lm.month_end)                                                 as oldest_overdue_due_date,
        count(*) filter (
            where (i.settled_date_any is null or i.settled_date_any > lm.month_end)
              and i.due_date < lm.month_end)                                                 as n_overdue
    from loan_months lm
    join installments i using (loan_id)
    group by 1, 2, 3, 4, 5, 6
),

measured as (
    select
        *,
        case when oldest_overdue_due_date is null then 0
             else month_end - oldest_overdue_due_date end                                    as dpd
    from state
),

fx as (
    select rate_date, currency, units_per_usd
    from {{ ref('int_fx_daily') }}
)

select
    m.loan_id,
    m.merchant_id,
    m.currency,
    m.disbursed_date,
    m.month,
    m.month_end,
    m.outstanding_local,
    m.n_overdue,
    m.oldest_overdue_due_date,
    m.dpd,
    (m.dpd > 30)                                                        as is_par30,
    fx.units_per_usd                                                    as fx_units_per_usd,
    cast(m.outstanding_local / fx.units_per_usd as decimal(18, 6))      as outstanding_usd
from measured m
join fx
  on fx.currency  = m.currency
 and fx.rate_date = m.month_end
