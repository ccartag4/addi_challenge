-- Q3. GMV in USD and loan count for the 2026-01 disbursement cohort (Bogotá month, A6).
-- Source: silver.fct_loan; the same figures are reproduced from gold.agg_merchant_monthly.
with from_fact as (
    select 'silver.fct_loan' as source, count(*) as loans, round(sum(principal_usd), 2) as gmv_usd
    from {{ ref('fct_loan') }}
    where disbursed_month = date '2026-01-01'
),
from_gold as (
    select 'gold.agg_merchant_monthly' as source, sum(disbursed_loans) as loans, round(sum(gmv_usd), 2) as gmv_usd
    from {{ ref('agg_merchant_monthly') }}
    where month = date '2026-01-01'
),
if_utc as (
    select 'silver.fct_loan, UTC month (for reference only)' as source, count(*) as loans, round(sum(principal_usd), 2) as gmv_usd
    from {{ ref('fct_loan') }}
    where date_trunc('month', cast(disbursed_at_utc as date)) = date '2026-01-01'
)
select * from from_fact
union all select * from from_gold
union all select * from if_utc
