-- Business test (DMBOK: consistency / completeness). The merchant-month aggregate must add back
-- to the facts it summarises; otherwise the Merchant team and the Risk team would again "ask
-- for the same numbers and get different answers". Returns one row per mismatched total.
{{ config(meta = {'dq_dimension': 'consistency'}) }}

with agg as (
    select
        sum(applications)            as applications,
        sum(applications_approved)   as applications_approved,
        sum(disbursed_loans)         as disbursed_loans,
        sum(gmv_usd)                 as gmv_usd,
        sum(fpd30_eligible_loans)    as fpd30_eligible_loans,
        sum(fpd30_loans)             as fpd30_loans,
        sum(outstanding_usd_month_end) filter (where month_end = cast('{{ var("snapshot_date") }}' as date)) as outstanding_usd_last_month,
        sum(par30_usd_month_end)       filter (where month_end = cast('{{ var("snapshot_date") }}' as date)) as par30_usd_last_month
    from {{ ref('agg_merchant_monthly') }}
),

facts as (
    select
        (select count(*) from {{ ref('fct_application') }} where is_valid)                          as applications,
        (select count(*) from {{ ref('fct_application') }} where is_approved)                       as applications_approved,
        (select count(*) from {{ ref('fct_loan') }})                                                as disbursed_loans,
        (select sum(principal_usd) from {{ ref('fct_loan') }})                                      as gmv_usd,
        (select count(*) from {{ ref('dm_loan_delinquency_snapshot') }} where is_fpd30_eligible)    as fpd30_eligible_loans,
        (select count(*) from {{ ref('dm_loan_delinquency_snapshot') }} where is_fpd30)             as fpd30_loans,
        (select sum(outstanding_usd) from {{ ref('dm_loan_delinquency_snapshot') }})                as outstanding_usd_last_month,
        (select sum(outstanding_usd) from {{ ref('dm_loan_delinquency_snapshot') }} where is_par30) as par30_usd_last_month
),

checks as (
    select 'applications'           as measure, a.applications::double            as agg_value, f.applications::double            as fact_value from agg a, facts f
    union all select 'applications_approved',   a.applications_approved,           f.applications_approved           from agg a, facts f
    union all select 'disbursed_loans',         a.disbursed_loans,                 f.disbursed_loans                 from agg a, facts f
    union all select 'gmv_usd',                 a.gmv_usd,                         f.gmv_usd                         from agg a, facts f
    union all select 'fpd30_eligible_loans',    a.fpd30_eligible_loans,            f.fpd30_eligible_loans            from agg a, facts f
    union all select 'fpd30_loans',             a.fpd30_loans,                     f.fpd30_loans                     from agg a, facts f
    union all select 'outstanding_usd_last_month', a.outstanding_usd_last_month,   f.outstanding_usd_last_month      from agg a, facts f
    union all select 'par30_usd_last_month',    a.par30_usd_last_month,            f.par30_usd_last_month            from agg a, facts f
)

select *
from checks
where abs(agg_value - fact_value) > 0.01
