-- DQ profiling 16 — FIFO allocation and installment status as of snapshot_date (A20–A23).
-- Yields business question 4 (FPD30 global and 2026-01 cohort) and a preview of question 5.
{% set as_of_date = "cast('" ~ var('snapshot_date') ~ "' as date)" %}
with a as (
    select * from {{ ref('int_payment_allocation') }}
),
s as (
    select * from {{ ref('fct_installment_status') }}
),
p as (
    select * from {{ ref('fct_payment') }}
),
per_loan_money as (
    select l.loan_id, l.currency,
           coalesce(sum(p.amount), 0)                                   as total_paid,
           (select sum(amount_due) from s where s.loan_id = l.loan_id)  as total_due,
           (select sum(paid_amount_any) from s where s.loan_id = l.loan_id) as total_allocated
    from {{ ref('fct_loan') }} l
    left join p using (loan_id)
    group by l.loan_id, l.currency
),
loan_state as (
    -- loan-level state as of the snapshot, the way dm_loan_delinquency_snapshot will compute it
    select
        loan_id, currency,
        sum(case when not is_settled then amount_due else 0 end)                as outstanding_local,
        max(case when is_overdue then as_of_date - due_date else 0 end)          as dpd
    from s
    group by 1, 2
),
fx as (
    select currency, units_per_usd from {{ ref('int_fx_daily') }} where rate_date = {{ as_of_date }}
),
loan_state_usd as (
    select ls.*, ls.outstanding_local / fx.units_per_usd as outstanding_usd
    from loan_state ls join fx using (currency)
)
select * from (values
    ( 1, 'allocation rows (payment x installment)',                       (select count(*) from a)::varchar),
    ( 2, 'payments with >= 1 allocation / with none (pure overpayment)',  (select count(distinct a.payment_id) || ' / ' || ((select count(*) from p) - count(distinct a.payment_id)) from a)),
    ( 3, 'payments split across 2+ installments',                         (select count(*) from (select payment_id from a group by 1 having count(*) > 1))::varchar),
    ( 4, 'installments funded by 2+ payments',                            (select count(*) from (select loan_id, installment_number from a group by 1, 2 having count(*) > 1))::varchar),
    ( 5, 'loans with unallocated excess (> 0.01)',                        (select count(*) from per_loan_money where total_paid - total_allocated > 0.01)::varchar),
    ( 6, 'unallocated excess by currency',                                (select string_agg(currency || '=' || format('{:,.2f}', x), ', ' order by currency) from (select currency, sum(total_paid - total_allocated) x from per_loan_money group by 1))),
    ( 7, 'installments as of snapshot: settled / partial / unpaid',       (select count(*) filter (where is_settled) || ' / ' || count(*) filter (where is_partially_paid) || ' / ' || count(*) filter (where paid_amount = 0) from s)),
    ( 8, 'installments: due by snapshot / not yet due',                   (select count(*) filter (where is_due) || ' / ' || count(*) filter (where not is_due) from s)),
    ( 9, 'installments overdue as of snapshot',                           (select count(*) from s where is_overdue)::varchar),
    (10, 'settled installments: early / on time / late 1-30 / late >30',  (select count(*) filter (where days_to_settle < 0) || ' / ' || count(*) filter (where days_to_settle = 0) || ' / ' || count(*) filter (where days_to_settle between 1 and 30) || ' / ' || count(*) filter (where days_to_settle > 30) from s where is_settled)),
    (11, 'median / max days_to_settle (settled)',                         (select median(days_to_settle) || ' / ' || max(days_to_settle) from s where is_settled)),
    (12, 'max days_past_due accrued (any installment)',                   (select max(days_past_due) from s)::varchar),
    (13, 'installments whose payment arrived after the snapshot',         (select count(*) from s where paid_amount_any > paid_amount)::varchar),
    (14, 'FPD30: eligible first installments (due <= snapshot - 30)',     (select count(*) from s where is_fpd30_eligible)::varchar),
    (15, 'FPD30: flagged (paid > 30 days late or unpaid > 30 days)',      (select count(*) from s where is_fpd30)::varchar),
    (16, 'FPD30 global (Q4)',                                             (select round(100.0 * count(*) filter (where is_fpd30) / count(*) filter (where is_fpd30_eligible), 4)::varchar || ' %' from s)),
    (17, 'FPD30 2026-01 cohort: eligible / flagged / rate (Q4)',          (select count(*) filter (where is_fpd30_eligible) || ' / ' || count(*) filter (where is_fpd30) || ' / ' || round(100.0 * count(*) filter (where is_fpd30) / count(*) filter (where is_fpd30_eligible), 4) || ' %' from s where disbursed_month = date '2026-01-01')),
    (18, 'FPD30 flagged: unpaid vs paid late',                            (select count(*) filter (where not is_settled) || ' unpaid / ' || count(*) filter (where is_settled) || ' paid late' from s where is_fpd30)),
    (19, 'loans with outstanding balance as of snapshot',                 (select count(*) from loan_state_usd where outstanding_local > 0)::varchar),
    (20, 'loans fully settled as of snapshot',                            (select count(*) from loan_state_usd where outstanding_local = 0)::varchar),
    (21, 'loans by DPD bucket as of snapshot',                            (select string_agg(b || '=' || n, ', ' order by o) from (select case when dpd = 0 then '0' when dpd <= 30 then '1-30' when dpd <= 60 then '31-60' when dpd <= 90 then '61-90' else '90+' end b, min(case when dpd = 0 then 0 when dpd <= 30 then 1 when dpd <= 60 then 2 when dpd <= 90 then 3 else 4 end) o, count(*) n from loan_state_usd group by 1))),
    (22, 'total outstanding USD at snapshot rate (Q5 preview)',           (select format('{:,.2f}', sum(outstanding_usd)) from loan_state_usd)),
    (23, 'PAR30 = outstanding USD of DPD > 30 / total (Q5 preview)',      (select round(100.0 * sum(outstanding_usd) filter (where dpd > 30) / sum(outstanding_usd), 4)::varchar || ' %' from loan_state_usd)),
    (24, 'snapshot FX rates used',                                        (select string_agg(currency || '=' || units_per_usd, ', ' order by currency) from fx))
) t(seq, metric, value)
order by seq
