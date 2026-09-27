-- Q6a. Top 5 merchants by GMV in USD, with their approval rate, FPD30 and PAR30 at the
-- snapshot month end. Source: gold.agg_merchant_monthly (category = current version's name
-- for display; per-month categories are in the aggregate itself).
with per_merchant as (
    select
        g.merchant_id,
        max(g.merchant_name)                                                as merchant_name,
        max(g.country)                                                      as country,
        sum(g.applications)                                                 as applications,
        sum(g.applications_approved)                                        as approved,
        sum(g.disbursed_loans)                                              as loans,
        sum(g.gmv_usd)                                                      as gmv_usd,
        sum(g.fpd30_eligible_loans)                                         as fpd30_eligible,
        sum(g.fpd30_loans)                                                  as fpd30_loans,
        sum(g.outstanding_usd_month_end) filter (where g.month = (select max(month) from {{ ref('agg_merchant_monthly') }})) as outstanding_usd,
        sum(g.par30_usd_month_end)       filter (where g.month = (select max(month) from {{ ref('agg_merchant_monthly') }})) as par30_usd
    from {{ ref('agg_merchant_monthly') }} g
    group by g.merchant_id
),
ranked as (
    select
        row_number() over (order by gmv_usd desc)           as gmv_rank,
        p.*,
        d.category                                          as current_category,
        d.n_versions                                        as scd2_versions,
        gmv_usd / sum(gmv_usd) over ()                      as gmv_share
    from per_merchant p
    join {{ ref('dim_merchant') }} d on d.merchant_id = p.merchant_id and d.is_current
)
select
    gmv_rank,
    merchant_id,
    merchant_name,
    country,
    current_category,
    scd2_versions,
    loans,
    round(gmv_usd, 2)                                       as gmv_usd,
    round(100 * gmv_share, 2)                               as gmv_share_pct,
    round(100.0 * approved / applications, 2)               as approval_rate_pct,
    round(100.0 * fpd30_loans / nullif(fpd30_eligible, 0), 2) as fpd30_pct,
    round(outstanding_usd, 2)                               as outstanding_usd_at_snapshot,
    round(100.0 * par30_usd / nullif(outstanding_usd, 0), 2) as par30_pct_at_snapshot
from ranked
where gmv_rank <= 5
order by gmv_rank
