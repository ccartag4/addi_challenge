-- DQ profiling 14 — Accuracy: from 112,339 delivered payment rows to effective payments (A9).
with c as (
    select * from {{ ref('int_payment_classified') }}
),
f as (
    select * from {{ ref('fct_payment') }}
),
per_loan as (
    select l.loan_id, l.total_amount_due, l.currency,
           count(f.payment_id) as n_payments, coalesce(sum(f.amount), 0) as paid
    from {{ ref('fct_loan') }} l
    left join f using (loan_id)
    group by 1, 2, 3
)
select * from (values
    ( 1, 'payment rows delivered (bronze)',                        (select count(*) from {{ ref('brz_payments') }})::varchar),
    ( 2, 'payment rows after dedup (staging)',                     (select count(*) from c)::varchar),
    ( 3, 'by class',                                               (select string_agg(payment_class || '=' || n, ', ' order by payment_class) from (select payment_class, count(*) n from c group by 1))),
    ( 4, 'voided payments hit by 2 reversal rows (F11)',           (select count(*) from c where n_reversal_rows = 2)::varchar),
    ( 5, 'effective payments on invalid loans',                    (select count(*) from c where payment_class = 'EFFECTIVE' and not loan_is_valid)::varchar),
    ( 6, 'effective payments (fct_payment)',                       (select count(*) from f)::varchar),
    ( 7, 'effective by source',                                    (select string_agg(source_system || '=' || n, ', ' order by source_system) from (select source_system, count(*) n from f group by 1))),
    ( 8, 'effective by method',                                    (select string_agg(payment_method || '=' || n, ', ' order by n desc) from (select payment_method, count(*) n from f group by 1))),
    ( 9, 'amount received by currency (local)',                    (select string_agg(currency || '=' || format('{:,.2f}', a), ', ' order by currency) from (select currency, sum(amount) a from f group by 1))),
    (10, 'amount received in USD (rate of payment date)',          (select format('{:,.2f}', sum(amount_usd)) from f)),
    (11, 'legacy_v1: last payment (Bogotá date / UTC ts)',         (select max(paid_date) || ' / ' || max(paid_at_utc) from f where source_system = 'legacy_v1')),
    (12, 'core_v2: first payment (Bogotá date / UTC ts)',          (select min(paid_date) || ' / ' || min(paid_at_utc) from f where source_system = 'core_v2')),
    (13, 'payments dated after the snapshot (' || '{{ var("snapshot_date") }}' || ')', (select count(*) from f where paid_date > cast('{{ var("snapshot_date") }}' as date))::varchar),
    (14, 'payments before their loan was disbursed',               (select count(*) from c where paid_at_utc < loan_disbursed_at_utc)::varchar),
    (15, 'payments per valid loan: min / median / max',            (select min(n_payments) || ' / ' || median(n_payments) || ' / ' || max(n_payments) from per_loan)),
    (16, 'valid loans with no effective payment yet',              (select count(*) from per_loan where n_payments = 0)::varchar),
    (17, 'valid loans paid in full or more (paid >= plan total)',  (select count(*) from per_loan where paid >= total_amount_due)::varchar),
    (18, 'valid loans overpaid (paid > plan total + 1 unit)',      (select count(*) from per_loan where paid > total_amount_due + 1)::varchar),
    (19, 'legacy payment size check: median amount / median installment', (select round(median(f.amount / i.med), 2)::varchar from f join (select loan_id, median(amount_due) med from {{ ref('stg_installments') }} group by 1) i using (loan_id) where f.source_system = 'legacy_v1'))
) t(seq, metric, value)
order by seq
