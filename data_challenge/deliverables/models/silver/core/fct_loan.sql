-- Silver / core. Grain: one row per valid loan (A5): its application exists, is not deleted
-- and is APPROVED. 27,955 of the 28,075 delivered loans; the 120 excluded ones are visible in
-- int_loan_validated with their reason (F7).
--
-- USD: principal / units_per_usd at the Bogotá disbursement date (A6, A7), taken from the
-- forward-filled daily calendar; the source rate date and staleness travel with the row.
-- Merchant: version in effect on the disbursement date (A14) via dim_merchant.
-- Customer: the application's resolved real customer (A4, A19), falling back to the loan's.
with valid_loans as (
    select * from {{ ref('int_loan_validated') }} where is_valid
),

installments as (
    select
        loan_id,
        count(*)            as n_installments,
        min(due_date)       as first_due_date,
        max(due_date)       as last_due_date,
        sum(amount_due)     as total_amount_due
    from {{ ref('stg_installments') }}
    group by loan_id
),

fx as (
    select rate_date, currency, units_per_usd, rate_source_date, days_stale
    from {{ ref('int_fx_daily') }}
),

merchant_versions as (
    select merchant_id, merchant_sk, category, valid_from, valid_to_effective
    from {{ ref('dim_merchant') }}
),

bridge as (
    select customer_id, person_sk
    from {{ ref('bridge_customer_person') }}
)

select
    v.loan_id,
    v.application_id,
    coalesce(v.app_customer_id, v.customer_id)                  as customer_id,
    v.customer_id                                               as loan_customer_id,
    b.person_sk,
    v.merchant_id,
    m.merchant_sk,
    m.category                                                  as merchant_category_at_disbursement,
    v.currency,
    v.principal,
    v.term_months,
    v.apr,
    v.status,
    v.disbursed_at_utc,
    v.disbursed_date,
    v.disbursed_month,
    fx.units_per_usd                                            as fx_units_per_usd,
    fx.rate_source_date                                         as fx_rate_source_date,
    fx.days_stale                                               as fx_days_stale,
    cast(v.principal / fx.units_per_usd as decimal(18, 6))      as principal_usd,
    v.requested_amount,
    v.approved_amount,
    v.application_created_date,
    v.disbursed_date - v.application_created_date               as days_application_to_disbursement,
    i.n_installments,
    i.first_due_date,
    i.last_due_date,
    i.total_amount_due
from valid_loans v
left join installments i using (loan_id)
left join fx
       on fx.currency  = v.currency
      and fx.rate_date = v.disbursed_date
left join merchant_versions m
       on m.merchant_id = v.merchant_id
      and v.disbursed_date between m.valid_from and m.valid_to_effective
left join bridge b
       on b.customer_id = coalesce(v.app_customer_id, v.customer_id)
