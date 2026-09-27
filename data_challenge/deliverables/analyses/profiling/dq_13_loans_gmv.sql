-- DQ profiling 13 — Loans, FX fill and GMV in USD. Yields business questions 2 and 3 and a
-- preview of question 6 (top merchants by GMV).
with v as (
    select * from {{ ref('int_loan_validated') }}
),
l as (
    select * from {{ ref('fct_loan') }}
),
by_merchant as (
    select
        l.merchant_id,
        m.merchant_name_current,
        m.category      as current_category,
        m.country,
        count(*)        as loans,
        sum(l.principal_usd) as gmv_usd,
        sum(l.principal_usd) / (select sum(principal_usd) from l) as share
    from l
    join {{ ref('dim_merchant') }} m on m.merchant_id = l.merchant_id and m.is_current
    group by 1, 2, 3, 4
)
select * from (values
    ( 1, 'loans delivered',                                            (select count(*) from v)::varchar),
    ( 2, 'excluded, by reason',                                        (select string_agg(exclusion_reason || '=' || n, ', ') from (select exclusion_reason, count(*) n from v where not is_valid group by 1))),
    ( 3, 'valid loans (Q2)',                                           (select count(*) from l)::varchar),
    ( 4, 'total GMV in USD (Q2)',                                      (select format('{:,.2f}', sum(principal_usd)) from l)),
    ( 5, 'GMV USD by currency',                                        (select string_agg(currency || '=' || format('{:,.2f}', g), ', ' order by currency) from (select currency, sum(principal_usd) g from l group by 1))),
    ( 6, 'loans by currency',                                          (select string_agg(currency || '=' || n, ', ' order by currency) from (select currency, count(*) n from l group by 1))),
    ( 7, 'cohort 2026-01: loans (Q3)',                                 (select count(*) from l where disbursed_month = date '2026-01-01')::varchar),
    ( 8, 'cohort 2026-01: GMV USD (Q3)',                               (select format('{:,.2f}', sum(principal_usd)) from l where disbursed_month = date '2026-01-01')),
    ( 9, 'cohort 2026-01 if UTC month were used (loans)',              (select count(*) from l where date_trunc('month', cast(disbursed_at_utc as date)) = date '2026-01-01')::varchar),
    (10, 'loans disbursed on a day with no published rate',            (select count(*) from l where fx_days_stale > 0)::varchar),
    (11, '  share of valid loans',                                     (select round(100.0 * count(*) filter (where fx_days_stale > 0) / count(*), 2)::varchar || ' %' from l)),
    (12, 'max FX staleness used (days)',                               (select max(fx_days_stale) from l)::varchar),
    (13, 'loans matched to a merchant version at disbursement',        (select count(merchant_sk) from l)::varchar),
    (14, 'loans on UNKNOWN-category versions',                         (select count(*) from l where merchant_category_at_disbursement = 'UNKNOWN')::varchar),
    (15, 'disbursement date range (Bogotá)',                           (select min(disbursed_date) || ' .. ' || max(disbursed_date) from l)),
    (16, 'days application -> disbursement: min / median / max',       (select min(d) || ' / ' || median(d) || ' / ' || max(d) from (select days_application_to_disbursement d from l))),
    (17, 'top 5 merchants by GMV USD (Q6 preview)',                    (select string_agg(merchant_id || ' ' || country || ' ' || current_category || ': ' || format('{:,.0f}', gmv_usd) || ' (' || round(100 * share, 2) || '%)', ' | ' order by gmv_usd desc) from (select * from by_merchant order by gmv_usd desc limit 5))),
    (18, 'top 1 / top 5 / top 20 share of GMV',                        (select round(100 * sum(share) filter (where rk <= 1), 2) || '% / ' || round(100 * sum(share) filter (where rk <= 5), 2) || '% / ' || round(100 * sum(share) filter (where rk <= 20), 2) || '%' from (select share, row_number() over (order by gmv_usd desc) rk from by_merchant))),
    (19, 'merchants with at least one valid loan',                     (select count(*) from by_merchant)::varchar)
) t(seq, metric, value)
order by seq
