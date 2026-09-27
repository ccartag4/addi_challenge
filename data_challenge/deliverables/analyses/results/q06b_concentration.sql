-- Q6b. What the GMV distribution says about the business and about concentration risk in the
-- portfolio metrics. Source: gold.agg_merchant_monthly and gold.dm_loan_delinquency_snapshot.
with per_merchant as (
    select
        merchant_id,
        max(country)                                                        as country,
        sum(gmv_usd)                                                        as gmv_usd,
        sum(fpd30_eligible_loans)                                           as fpd30_eligible,
        sum(fpd30_loans)                                                    as fpd30_loans,
        sum(outstanding_usd_month_end) filter (where month = (select max(month) from {{ ref('agg_merchant_monthly') }})) as outstanding_usd,
        sum(par30_usd_month_end)       filter (where month = (select max(month) from {{ ref('agg_merchant_monthly') }})) as par30_usd
    from {{ ref('agg_merchant_monthly') }}
    group by merchant_id
),
ranked as (
    select *, row_number() over (order by gmv_usd desc) as rk,
           sum(gmv_usd) over (order by gmv_usd desc) / sum(gmv_usd) over () as cum_share
    from per_merchant
),
seg as (
    select case when rk = 1 then '1. top 1 (merchant 1607)'
                when rk <= 5 then '2. rank 2-5'
                when rk <= 20 then '3. rank 6-20'
                else '4. rank 21-698' end as segment,
           count(*) merchants, sum(gmv_usd) gmv_usd, sum(fpd30_loans) fpd30_loans, sum(fpd30_eligible) fpd30_eligible,
           sum(outstanding_usd) outstanding_usd, sum(par30_usd) par30_usd
    from ranked group by 1
),
total as (
    select '0. portfolio' as segment, count(*) merchants, sum(gmv_usd) gmv_usd, sum(fpd30_loans) fpd30_loans, sum(fpd30_eligible) fpd30_eligible,
           sum(outstanding_usd) outstanding_usd, sum(par30_usd) par30_usd
    from ranked
),
without_top as (
    select '5. portfolio without merchant 1607' as segment, count(*) merchants, sum(gmv_usd) gmv_usd, sum(fpd30_loans) fpd30_loans, sum(fpd30_eligible) fpd30_eligible,
           sum(outstanding_usd) outstanding_usd, sum(par30_usd) par30_usd
    from ranked where rk > 1
),
by_country as (
    select '6. country ' || country as segment, count(*) merchants, sum(gmv_usd) gmv_usd, sum(fpd30_loans) fpd30_loans, sum(fpd30_eligible) fpd30_eligible,
           sum(outstanding_usd) outstanding_usd, sum(par30_usd) par30_usd
    from ranked group by country
),
all_rows as (
    select * from total union all select * from seg union all select * from without_top union all select * from by_country
)
select
    segment,
    merchants,
    round(gmv_usd, 0)                                                       as gmv_usd,
    round(100.0 * gmv_usd / (select gmv_usd from total), 2)                 as gmv_share_pct,
    round(100.0 * fpd30_loans / nullif(fpd30_eligible, 0), 2)               as fpd30_pct,
    round(outstanding_usd, 0)                                               as outstanding_usd_at_snapshot,
    round(100.0 * outstanding_usd / (select outstanding_usd from total), 2) as outstanding_share_pct,
    round(100.0 * par30_usd / nullif(outstanding_usd, 0), 2)                as par30_pct_at_snapshot,
    (select min(rk) from ranked where cum_share >= 0.5)                     as merchants_for_50pct_gmv,
    (select min(rk) from ranked where cum_share >= 0.8)                     as merchants_for_80pct_gmv
from all_rows
order by segment
