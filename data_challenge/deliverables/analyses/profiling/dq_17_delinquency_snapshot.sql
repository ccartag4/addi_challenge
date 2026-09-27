-- DQ profiling 17 — Delinquency snapshot as of snapshot_date. Yields business question 5
-- (PAR30 and total outstanding balance in USD) plus the sensitivity of that figure to the
-- definitions left open by the README (A11 gross vs net of partial, A12 snapshot vs
-- disbursement rate).
with d as (
    select * from {{ ref('dm_loan_delinquency_snapshot') }}
),
buckets as (
    select dpd_bucket,
           min(case dpd_bucket when '0' then 0 when '1-30' then 1 when '31-60' then 2 when '61-90' then 3 else 4 end) as o,
           count(*) as loans,
           sum(outstanding_usd) as usd
    from d group by 1
)
select * from (values
    ( 1, 'loans in snapshot (= valid loans)',                                 (select count(*) from d)::varchar),
    ( 2, 'as_of_date / FX rates used',                                        (select min(as_of_date) || ' / ' || string_agg(distinct currency || '=' || fx_units_per_usd_at_snapshot, ', ') from d)),
    ( 3, 'loans by status',                                                   (select string_agg(loan_status || '=' || n, ', ' order by loan_status) from (select loan_status, count(*) n from d group by 1))),
    ( 4, 'loans by DPD bucket (loans / outstanding USD / share of USD)',      (select string_agg(dpd_bucket || ': ' || loans || ' / ' || format('{:,.0f}', usd) || ' / ' || round(100 * usd / (select sum(outstanding_usd) from d), 2) || '%', ' | ' order by o) from buckets)),
    ( 5, 'total outstanding balance USD (Q5)',                                (select format('{:,.2f}', sum(outstanding_usd)) from d)),
    ( 6, 'outstanding USD of loans with DPD > 30 (PAR30 numerator)',          (select format('{:,.2f}', sum(outstanding_usd) filter (where is_par30)) from d)),
    ( 7, 'PAR30 (Q5)',                                                        (select round(100.0 * sum(outstanding_usd) filter (where is_par30) / sum(outstanding_usd), 4)::varchar || ' %' from d)),
    ( 8, 'loans with DPD > 30 / loans with balance',                          (select count(*) filter (where is_par30) || ' / ' || count(*) filter (where outstanding_local > 0) from d)),
    ( 9, 'outstanding by currency: local / USD',                              (select string_agg(currency || ': ' || format('{:,.2f}', loc) || ' / ' || format('{:,.2f}', usd), ' | ' order by currency) from (select currency, sum(outstanding_local) loc, sum(outstanding_usd) usd from d group by 1))),
    (10, 'PAR30 by currency',                                                 (select string_agg(currency || '=' || r || '%', ', ' order by currency) from (select currency, round(100.0 * sum(outstanding_usd) filter (where is_par30) / sum(outstanding_usd), 2) r from d group by 1))),
    (11, 'sensitivity A11: outstanding net of partial payments (USD) / PAR30', (select format('{:,.2f}', sum(outstanding_net_of_partial_usd)) || ' / ' || round(100.0 * sum(outstanding_net_of_partial_usd) filter (where is_par30) / sum(outstanding_net_of_partial_usd), 4) || ' %' from d)),
    (12, 'sensitivity A12: outstanding at disbursement-date rates (USD) / PAR30', (select format('{:,.2f}', sum(outstanding_usd_at_disbursement_rate)) || ' / ' || round(100.0 * sum(outstanding_usd_at_disbursement_rate) filter (where is_par30) / sum(outstanding_usd_at_disbursement_rate), 4) || ' %' from d)),
    (13, 'overdue amount USD (installments already due and unpaid)',          (select format('{:,.2f}', sum(overdue_amount_usd)) from d)),
    (14, 'delinquent loans: median / max days since last payment',            (select median(days_since_last_payment) || ' / ' || max(days_since_last_payment) from d where loan_status = 'DELINQUENT' and last_payment_date is not null)),
    (15, 'delinquent loans that never paid anything',                         (select count(*) from d where loan_status = 'DELINQUENT' and paid_amount = 0)::varchar),
    (16, 'PAR30 by disbursement year',                                        (select string_agg(y || '=' || r || '%', ', ' order by y) from (select extract(year from disbursed_date) y, round(100.0 * sum(outstanding_usd) filter (where is_par30) / sum(outstanding_usd), 2) r from d group by 1))),
    (17, 'consistency with dq_16: FPD30 eligible / flagged from the mart',    (select count(*) filter (where is_fpd30_eligible) || ' / ' || count(*) filter (where is_fpd30) from d)),
    (18, 'top 5 merchants by outstanding USD (share of total)',               (select string_agg(merchant_id || ': ' || format('{:,.0f}', usd) || ' (' || round(100 * usd / (select sum(outstanding_usd) from d), 2) || '%)', ' | ' order by usd desc) from (select merchant_id, sum(outstanding_usd) usd from d group by 1 order by 2 desc limit 5)))
) t(seq, metric, value)
order by seq
