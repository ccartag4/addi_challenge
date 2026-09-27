-- DQ profiling 18 — agg_merchant_monthly: shape, reconciliation against the facts, and the
-- answer to business question 6 (top merchants by GMV and what the concentration does to the
-- portfolio metrics).
with g as (
    select * from {{ ref('agg_merchant_monthly') }}
),
last_month as (
    select max(month) as month from g
),
per_merchant as (
    select
        merchant_id,
        max(merchant_name)                                                  as merchant_name,
        max(country)                                                        as country,
        sum(applications)                                                   as applications,
        sum(applications_approved)                                          as approved,
        sum(disbursed_loans)                                                as loans,
        sum(gmv_usd)                                                        as gmv_usd,
        sum(fpd30_eligible_loans)                                           as fpd30_eligible,
        sum(fpd30_loans)                                                    as fpd30_loans,
        sum(outstanding_usd_month_end) filter (where month = (select month from last_month)) as outstanding_usd,
        sum(par30_usd_month_end)       filter (where month = (select month from last_month)) as par30_usd
    from g
    group by merchant_id
),
ranked as (
    select *,
           row_number() over (order by gmv_usd desc)                        as gmv_rank,
           gmv_usd / sum(gmv_usd) over ()                                   as gmv_share
    from per_merchant
),
groups as (
    select case when gmv_rank <= 5 then 'top 5' else 'other 693' end as grp,
           sum(gmv_usd) gmv_usd, sum(fpd30_loans) fpd30_loans, sum(fpd30_eligible) fpd30_eligible,
           sum(outstanding_usd) outstanding_usd, sum(par30_usd) par30_usd
    from ranked group by 1
)
select * from (values
    ( 1, 'rows / merchants / months',                                  (select count(*) || ' / ' || count(distinct merchant_id) || ' / ' || count(distinct month) from g)),
    ( 2, 'month range',                                                (select min(month) || ' .. ' || max(month) from g)),
    ( 3, 'rows with activity / without',                               (select count(*) filter (where has_activity) || ' / ' || count(*) filter (where not has_activity) from g)),
    ( 4, 'merchant-months where the category changed inside the month', (select count(*) from g where category_changed_in_month)::varchar),
    ( 5, 'rows under UNKNOWN category',                                (select count(*) from g where merchant_category = 'UNKNOWN')::varchar),
    ( 6, 'reconciliation Q1: applications / approved / rate',         (select sum(applications) || ' / ' || sum(applications_approved) || ' / ' || round(100.0 * sum(applications_approved) / sum(applications), 4) || ' %' from g)),
    ( 7, 'reconciliation Q2: loans / GMV USD',                         (select sum(disbursed_loans) || ' / ' || format('{:,.2f}', sum(gmv_usd)) from g)),
    ( 8, 'reconciliation Q3: 2026-01 loans / GMV USD',                 (select sum(disbursed_loans) || ' / ' || format('{:,.2f}', sum(gmv_usd)) from g where month = date '2026-01-01')),
    ( 9, 'reconciliation Q4: FPD30 global / 2026-01 cohort',           (select round(100.0 * sum(fpd30_loans) / sum(fpd30_eligible_loans), 4) || ' % / ' || (select round(100.0 * sum(fpd30_loans) / sum(fpd30_eligible_loans), 4) from g where month = date '2026-01-01') || ' %' from g)),
    (10, 'reconciliation Q5: outstanding USD / PAR30 at last month end', (select format('{:,.2f}', sum(outstanding_usd_month_end)) || ' / ' || round(100.0 * sum(par30_usd_month_end) / sum(outstanding_usd_month_end), 4) || ' %' from g where month = (select month from last_month))),
    (11, 'portfolio PAR30 by month end (stock)',                       (select string_agg(strftime(month, '%Y-%m') || '=' || round(100.0 * p / o, 1) || '%', ', ' order by month) from (select month, sum(par30_usd_month_end) p, sum(outstanding_usd_month_end) o from g group by 1 having sum(outstanding_usd_month_end) > 0))),
    (12, 'portfolio FPD30 by disbursement month (cohort)',             (select string_agg(strftime(month, '%Y-%m') || '=' || round(100.0 * f / e, 1) || '%', ', ' order by month) from (select month, sum(fpd30_loans) f, sum(fpd30_eligible_loans) e from g group by 1 having sum(fpd30_eligible_loans) > 0))),
    (13, 'Q6 top 5 by GMV: id country | GMV USD (share) | approval | FPD30 | PAR30 at snapshot', (select string_agg(merchant_id || ' ' || country || ' | ' || format('{:,.0f}', gmv_usd) || ' (' || round(100 * gmv_share, 2) || '%) | ' || round(100.0 * approved / applications, 1) || '% | ' || round(100.0 * fpd30_loans / nullif(fpd30_eligible, 0), 2) || '% | ' || round(100.0 * par30_usd / nullif(outstanding_usd, 0), 2) || '%', ' || ' order by gmv_rank) from ranked where gmv_rank <= 5)),
    (14, 'Q6 top 5 vs the rest: GMV share | FPD30 | PAR30 at snapshot', (select string_agg(grp || ': ' || round(100.0 * gmv_usd / (select sum(gmv_usd) from groups), 2) || '% | ' || round(100.0 * fpd30_loans / fpd30_eligible, 2) || '% | ' || round(100.0 * par30_usd / outstanding_usd, 2) || '%', ' || ' order by grp) from groups)),
    (15, 'Q6 portfolio FPD30 / PAR30 excluding merchant 1607',         (select round(100.0 * sum(fpd30_loans) / sum(fpd30_eligible), 4) || ' % / ' || round(100.0 * sum(par30_usd) / sum(outstanding_usd), 4) || ' %' from per_merchant where merchant_id <> 1607)),
    (16, 'Q6 GMV concentration: top 1 / 5 / 20 share, merchants for 50 % / 80 % of GMV', (select round(100 * max(case when gmv_rank = 1 then cum end), 2) || '% / ' || round(100 * max(case when gmv_rank = 5 then cum end), 2) || '% / ' || round(100 * max(case when gmv_rank = 20 then cum end), 2) || '% ; ' || min(case when cum >= 0.5 then gmv_rank end) || ' / ' || min(case when cum >= 0.8 then gmv_rank end) from (select gmv_rank, sum(gmv_share) over (order by gmv_rank) cum from ranked))),
    (17, 'merchant 1607: PAR30 month-end vs cohort view at snapshot month', (select round(100 * par30_rate, 2) || '% month-end vs ' || round(100 * par30_cohort_rate_at_snapshot, 2) || '% cohort (' || strftime(month, '%Y-%m') || ')' from g where merchant_id = 1607 and month = (select month from last_month))),
    (18, 'GMV share by merchant country',                              (select string_agg(country || '=' || round(100.0 * s / (select sum(gmv_usd) from g), 2) || '%', ', ' order by country) from (select country, sum(gmv_usd) s from g group by 1)))
) t(seq, metric, value)
order by seq
