-- DQ profiling 05 — Payments: two source systems, reference formats, amount scale, reversals.
with p_raw as (
    select * exclude (_brz_source_file, _brz_built_at) from {{ ref('brz_payments') }}
),
p as (select distinct * from p_raw),
p_num as (
    select
        *,
        regexp_extract(loan_ref, '(\d+)$', 1)  as loan_id_norm,
        try_cast(amount_raw as double)          as amt
    from p
),
settled as (select * from p_num where status = 'SETTLED'),
rev     as (select * from p_num where status = 'REVERSED'),
loans   as (select loan_id, currency from {{ ref('brz_loans') }}),
inst_med as (
    select loan_id, median(try_cast(amount_due as double)) as med_due
    from {{ ref('brz_installments') }}
    group by 1
),
-- Scale check: a settled payment should be about the size of one installment.
-- If a source reports in minor units the ratio lands near 100 instead of 1.
scale as (
    select
        s.source_system,
        l.currency,
        count(*)                                     as n_payments,
        round(median(s.amt / nullif(m.med_due, 0)), 2) as median_amount_over_installment
    from settled s
    join loans    l on l.loan_id = s.loan_id_norm
    join inst_med m on m.loan_id = s.loan_id_norm
    group by 1, 2
)
select * from (values
    ( 1, 'rows',                                                    (select count(*) from p_raw)::varchar),
    ( 2, 'rows after exact dedup',                                  (select count(*) from p)::varchar),
    ( 3, 'distinct payment_id',                                     (select count(distinct payment_id) from p)::varchar),
    ( 4, 'payment_id with >1 distinct row after dedup',             (select count(*) from (select payment_id from p group by 1 having count(*) > 1))::varchar),
    ( 5, 'columns that differ within those payment_ids',            (select string_agg(distinct
                                                                        case when a.paid_at_utc <> b.paid_at_utc then 'paid_at_utc'
                                                                             when a.amount_raw <> b.amount_raw then 'amount_raw'
                                                                             when a.status <> b.status then 'status'
                                                                             when a.loan_ref <> b.loan_ref then 'loan_ref'
                                                                             else 'other' end, ', ')
                                                                     from p a join p b on a.payment_id = b.payment_id and a.paid_at_utc < b.paid_at_utc)),
    ( 6, 'source_system x status',                                  (select string_agg(source_system || '/' || status || '=' || n, ', ' order by source_system, status)
                                                                     from (select source_system, status, count(*) n from p group by 1, 2))),
    ( 7, 'loan_ref shapes by source',                               (select string_agg(source_system || ': ' || shape || ' x' || n, ' | ' order by source_system)
                                                                     from (select source_system, regexp_replace(loan_ref, '\d', '9', 'g') shape, count(*) n from p group by 1, 2))),
    ( 8, 'payment_method values',                                   (select string_agg(distinct payment_method, ', ') from p)),
    ( 9, 'REVERSED rows with null reversed_payment_id',             (select count(*) from rev where reversed_payment_id is null)::varchar),
    (10, 'REVERSED rows whose target payment_id does not exist',    (select count(*) from rev r where not exists (select 1 from p_num t where t.payment_id = r.reversed_payment_id))::varchar),
    (11, 'REVERSED rows whose target is itself REVERSED',           (select count(*) from rev r where exists (select 1 from rev t where t.payment_id = r.reversed_payment_id))::varchar),
    (12, 'target payments reversed by >1 reversal row',             (select count(*) from (select reversed_payment_id from rev group by 1 having count(*) > 1))::varchar),
    (13, 'REVERSED rows with negative amount',                      (select count(*) from rev where amt < 0)::varchar),
    (14, 'REVERSED rows where |amount| <> target amount',           (select count(*) from rev r join settled t on t.payment_id = r.reversed_payment_id where abs(r.amt) <> t.amt)::varchar),
    (15, 'REVERSED rows in a different source than their target',   (select count(*) from rev r join settled t on t.payment_id = r.reversed_payment_id where r.source_system <> t.source_system)::varchar),
    (16, 'SETTLED rows with amount <= 0 or null',                   (select count(*) from settled where coalesce(amt, 0) <= 0)::varchar),
    (17, 'payments whose normalized loan ref is not in loans',      (select count(*) from p_num where loan_id_norm not in (select loan_id from loans))::varchar),
    (18, 'median amount / median installment — legacy_v1 COP',      (select median_amount_over_installment::varchar from scale where source_system = 'legacy_v1' and currency = 'COP')),
    (19, 'median amount / median installment — legacy_v1 BRL',      (select median_amount_over_installment::varchar from scale where source_system = 'legacy_v1' and currency = 'BRL')),
    (20, 'median amount / median installment — core_v2 COP',        (select median_amount_over_installment::varchar from scale where source_system = 'core_v2'   and currency = 'COP')),
    (21, 'median amount / median installment — core_v2 BRL',        (select median_amount_over_installment::varchar from scale where source_system = 'core_v2'   and currency = 'BRL'))
) t(seq, metric, value)
order by seq
