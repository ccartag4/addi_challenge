-- DQ profiling 04 — Loans and installments: referential integrity and consistency with the
-- originating application.
with cdc as (
    select distinct * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_applications_cdc') }}
),
app_ids as (select distinct application_id from cdc),
deleted as (select distinct application_id from cdc where _op = 'D'),
loans as (
    select * exclude (_brz_source_file, _brz_built_at) from {{ ref('brz_loans') }}
),
inst as (
    select distinct loan_id, installment_number from {{ ref('brz_installments') }}
),
inst_cnt as (select loan_id, count(*) as n from inst group by 1),
loans_with_app as (
    select l.* from loans l where exists (select 1 from app_ids a where a.application_id = l.application_id)
)
select * from (values
    ( 1, 'loan rows',                                                       (select count(*) from loans)::varchar),
    ( 2, 'distinct loan_id',                                                (select count(distinct loan_id) from loans)::varchar),
    ( 3, 'status values',                                                   (select string_agg(distinct status, ', ') from loans)),
    ( 4, 'currency values',                                                 (select string_agg(distinct currency, ', ') from loans)),
    ( 5, 'term_months values',                                              (select string_agg(distinct term_months, ', ' order by term_months) from loans)),
    ( 6, 'loans whose application_id is not in the CDC at all',             (select count(*) from loans l where not exists (select 1 from app_ids a where a.application_id = l.application_id))::varchar),
    ( 7, 'loans whose application has a D event',                           (select count(*) from loans l where exists (select 1 from deleted d where d.application_id = l.application_id))::varchar),
    ( 8, 'loans whose customer_id never appears on their application',      (select count(*) from loans_with_app l where not exists (select 1 from cdc c where c.application_id = l.application_id and c.customer_id = l.customer_id))::varchar),
    ( 9, 'loans whose merchant_id never appears on their application',      (select count(*) from loans_with_app l where not exists (select 1 from cdc c where c.application_id = l.application_id and c.merchant_id = l.merchant_id))::varchar),
    (10, 'loans whose currency never appears on their application',         (select count(*) from loans_with_app l where not exists (select 1 from cdc c where c.application_id = l.application_id and c.currency = l.currency))::varchar),
    (11, 'loans whose principal <> any approved_amount of their application', (select count(*) from loans_with_app l where not exists (select 1 from cdc c where c.application_id = l.application_id and abs(try_cast(c.approved_amount as double) - try_cast(l.principal as double)) < 0.01))::varchar),
    (12, 'loans with principal <= 0 or null',                               (select count(*) from loans where coalesce(try_cast(principal as double), 0) <= 0)::varchar),
    (13, 'applications with >1 loan',                                       (select count(*) from (select application_id from loans group by 1 having count(*) > 1))::varchar),
    (14, 'loans without installments',                                      (select count(*) from loans l where not exists (select 1 from inst i where i.loan_id = l.loan_id))::varchar),
    (15, 'loans where #installments <> term_months',                        (select count(*) from loans l join inst_cnt c on c.loan_id = l.loan_id where c.n <> try_cast(l.term_months as integer))::varchar),
    (16, 'installment rows whose loan_id is not in loans',                  (select count(*) from inst i where not exists (select 1 from loans l where l.loan_id = i.loan_id))::varchar),
    (17, 'installments with amount_due <= 0 or null',                       (select count(*) from {{ ref('brz_installments') }} where coalesce(try_cast(amount_due as double), 0) <= 0)::varchar),
    (18, 'installment due_date range',                                      (select min(due_date) || ' .. ' || max(due_date) from {{ ref('brz_installments') }}))
) t(seq, metric, value)
order by seq
