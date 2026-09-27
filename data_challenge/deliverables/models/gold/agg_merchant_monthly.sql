-- Gold / consumption. Grain: merchant x month (README 4.1 gold 1), dense from the first month
-- with activity to the snapshot month, for every month in which the merchant already existed.
--
-- Flows are counted in the month of their Bogotá event date:
--   applications, applications_approved, approval_rate   applications created in the month (A14)
--   disbursed_loans, gmv_usd                              loans disbursed in the month (A6, A7)
--   fpd30_*                                               cohort of loans disbursed in the month,
--                                                         measured as of the snapshot (A23)
-- Stock is measured at the month end (A13):
--   outstanding_usd_month_end, par30_usd_month_end, par30_rate   from int_loan_month_end_status
-- A cohort view of PAR30 as of the snapshot is kept as a clearly named secondary column.
--
-- merchant_category is the category in effect at the month end (A25). Rows where the merchant
-- changed category inside the month are flagged with the earlier category.
{% set as_of_date = "cast('" ~ var('snapshot_date') ~ "' as date)" %}

with bounds as (
    select
        least(
            (select min(created_month)   from {{ ref('fct_application') }} where is_valid),
            (select min(disbursed_month) from {{ ref('fct_loan') }})
        )                                                               as first_month,
        cast(date_trunc('month', {{ as_of_date }}) as date)             as last_month
),

months as (
    select
        cast(m as date)                                                 as month,
        cast(last_day(cast(m as date)) as date)                         as month_end
    from (select unnest(generate_series(first_month, last_month, interval 1 month)) as m from bounds)
),

merchants as (
    select merchant_id, min(valid_from) as first_valid_from
    from {{ ref('dim_merchant') }}
    group by merchant_id
),

grid as (
    select mr.merchant_id, mo.month, mo.month_end
    from merchants mr
    cross join months mo
    where mo.month_end >= mr.first_valid_from
),

category_end as (
    select g.merchant_id, g.month, d.merchant_sk, d.category, d.merchant_name_current, d.country
    from grid g
    join {{ ref('dim_merchant') }} d
      on d.merchant_id = g.merchant_id
     and g.month_end between d.valid_from and d.valid_to_effective
),

category_start as (
    select g.merchant_id, g.month, d.category as category_at_month_start
    from grid g
    left join {{ ref('dim_merchant') }} d
      on d.merchant_id = g.merchant_id
     and g.month between d.valid_from and d.valid_to_effective
),

apps as (
    select
        merchant_id,
        created_month                                       as month,
        count(*) filter (where is_valid)                    as applications,
        count(*) filter (where is_approved)                 as applications_approved,
        count(*) filter (where is_deleted)                  as applications_deleted
    from {{ ref('fct_application') }}
    group by 1, 2
),

cohort as (
    select
        merchant_id,
        disbursed_month                                     as month,
        count(*)                                            as disbursed_loans,
        sum(principal_usd)                                  as gmv_usd,
        count(*) filter (where is_fpd30_eligible)           as fpd30_eligible_loans,
        count(*) filter (where is_fpd30)                    as fpd30_loans,
        coalesce(sum(outstanding_usd), 0)                   as cohort_outstanding_usd_at_snapshot,
        coalesce(sum(outstanding_usd) filter (where is_par30), 0) as cohort_par30_usd_at_snapshot
    from {{ ref('dm_loan_delinquency_snapshot') }}
    group by 1, 2
),

stock as (
    select
        merchant_id,
        month,
        count(*) filter (where outstanding_local > 0)       as loans_with_balance_month_end,
        count(*) filter (where is_par30)                    as loans_par30_month_end,
        coalesce(sum(outstanding_usd), 0)                   as outstanding_usd_month_end,
        coalesce(sum(outstanding_usd) filter (where is_par30), 0) as par30_usd_month_end
    from {{ ref('int_loan_month_end_status') }}
    group by 1, 2
)

select
    g.merchant_id,
    g.month,
    g.month_end,
    ce.merchant_sk,
    ce.merchant_name_current                                                    as merchant_name,
    ce.country,
    ce.category                                                                 as merchant_category,
    cs.category_at_month_start,
    -- NULL at month start = the merchant's first version began inside this month: not a change
    (cs.category_at_month_start is not null
        and cs.category_at_month_start <> ce.category)                          as category_changed_in_month,
    -- applications (flow, creation month)
    coalesce(a.applications, 0)                                                 as applications,
    coalesce(a.applications_approved, 0)                                        as applications_approved,
    coalesce(a.applications_deleted, 0)                                         as applications_deleted,
    case when coalesce(a.applications, 0) > 0
         then cast(a.applications_approved as decimal(18, 6)) / a.applications end as approval_rate,
    -- loans (flow, disbursement month)
    coalesce(c.disbursed_loans, 0)                                              as disbursed_loans,
    coalesce(c.gmv_usd, 0)                                                      as gmv_usd,
    -- FPD30 (cohort of the disbursement month, as of the snapshot)
    coalesce(c.fpd30_eligible_loans, 0)                                         as fpd30_eligible_loans,
    coalesce(c.fpd30_loans, 0)                                                  as fpd30_loans,
    case when coalesce(c.fpd30_eligible_loans, 0) > 0
         then cast(c.fpd30_loans as decimal(18, 6)) / c.fpd30_eligible_loans end   as fpd30_rate,
    -- PAR30 (stock at month end)
    coalesce(s.loans_with_balance_month_end, 0)                                 as loans_with_balance_month_end,
    coalesce(s.loans_par30_month_end, 0)                                        as loans_par30_month_end,
    coalesce(s.outstanding_usd_month_end, 0)                                    as outstanding_usd_month_end,
    coalesce(s.par30_usd_month_end, 0)                                          as par30_usd_month_end,
    case when coalesce(s.outstanding_usd_month_end, 0) > 0
         then s.par30_usd_month_end / s.outstanding_usd_month_end end            as par30_rate,
    -- PAR30 cohort view (secondary, A13 alternative)
    coalesce(c.cohort_outstanding_usd_at_snapshot, 0)                           as cohort_outstanding_usd_at_snapshot,
    coalesce(c.cohort_par30_usd_at_snapshot, 0)                                 as cohort_par30_usd_at_snapshot,
    case when coalesce(c.cohort_outstanding_usd_at_snapshot, 0) > 0
         then c.cohort_par30_usd_at_snapshot / c.cohort_outstanding_usd_at_snapshot end as par30_cohort_rate_at_snapshot,
    (coalesce(a.applications, 0) + coalesce(c.disbursed_loans, 0)
        + coalesce(s.loans_with_balance_month_end, 0)) > 0                      as has_activity
from grid g
join category_end   ce using (merchant_id, month)
left join category_start cs using (merchant_id, month)
left join apps   a using (merchant_id, month)
left join cohort c using (merchant_id, month)
left join stock  s using (merchant_id, month)
