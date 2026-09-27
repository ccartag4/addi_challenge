-- DQ profiling 15 — Row-count funnel: how many rows each extract has at every layer, and the
-- delta between consecutive layers. The *reason* for each delta is documented in
-- DATA_JOURNEY.md (section A) with its finding / assumption number; this analysis is the
-- evidence that the numbers there are real.
with counts as (
    -- applications
    select 'applications_cdc' as extract, 1 as stage, 'bronze.brz_applications_cdc'                 as model, count(*) as n from {{ ref('brz_applications_cdc') }}
    union all select 'applications_cdc', 2, 'silver.stg_applications_cdc',                                    count(*) from {{ ref('stg_applications_cdc') }}
    union all select 'applications_cdc', 3, 'silver.int_application_events',                                  count(*) from {{ ref('int_application_events') }}
    union all select 'applications_cdc', 4, 'silver.fct_application (all applications)',                      count(*) from {{ ref('fct_application') }}
    union all select 'applications_cdc', 5, 'silver.fct_application where is_valid',                          count(*) from {{ ref('fct_application') }} where is_valid
    union all select 'applications_cdc', 6, 'silver.fct_application where is_approved',                       count(*) from {{ ref('fct_application') }} where is_approved
    -- loans
    union all select 'loans', 1, 'bronze.brz_loans',                                                          count(*) from {{ ref('brz_loans') }}
    union all select 'loans', 2, 'silver.stg_loans',                                                          count(*) from {{ ref('stg_loans') }}
    union all select 'loans', 3, 'silver.int_loan_validated',                                                 count(*) from {{ ref('int_loan_validated') }}
    union all select 'loans', 4, 'silver.fct_loan (valid loans)',                                             count(*) from {{ ref('fct_loan') }}
    -- installments
    union all select 'installments', 1, 'bronze.brz_installments',                                            count(*) from {{ ref('brz_installments') }}
    union all select 'installments', 2, 'silver.stg_installments',                                            count(*) from {{ ref('stg_installments') }}
    union all select 'installments', 3, 'silver.stg_installments on valid loans',                             count(*) from {{ ref('stg_installments') }} where loan_id in (select loan_id from {{ ref('fct_loan') }})
    -- payments
    union all select 'payments', 1, 'bronze.brz_payments',                                                    count(*) from {{ ref('brz_payments') }}
    union all select 'payments', 2, 'silver.stg_payments',                                                    count(*) from {{ ref('stg_payments') }}
    union all select 'payments', 3, 'silver.int_payment_classified',                                          count(*) from {{ ref('int_payment_classified') }}
    union all select 'payments', 4, 'silver.int_payment_classified where EFFECTIVE',                          count(*) from {{ ref('int_payment_classified') }} where payment_class = 'EFFECTIVE'
    union all select 'payments', 5, 'silver.fct_payment (effective, valid loans)',                            count(*) from {{ ref('fct_payment') }}
    -- customers
    union all select 'customers', 1, 'bronze.brz_customers',                                                  count(*) from {{ ref('brz_customers') }}
    union all select 'customers', 2, 'silver.stg_customers',                                                  count(*) from {{ ref('stg_customers') }}
    union all select 'customers', 3, 'silver.bridge_customer_person (customer_id grain)',                     count(*) from {{ ref('bridge_customer_person') }}
    union all select 'customers', 4, 'silver.dim_customer (person grain)',                                    count(*) from {{ ref('dim_customer') }}
    -- merchants
    union all select 'merchants_history', 1, 'bronze.brz_merchants_history',                                  count(*) from {{ ref('brz_merchants_history') }}
    union all select 'merchants_history', 2, 'silver.stg_merchants_history',                                  count(*) from {{ ref('stg_merchants_history') }}
    union all select 'merchants_history', 3, 'silver.dim_merchant (versions)',                                count(*) from {{ ref('dim_merchant') }}
    union all select 'merchants_history', 4, 'silver.dim_merchant where is_current (merchants)',              count(*) from {{ ref('dim_merchant') }} where is_current
    -- fx
    union all select 'fx_rates', 1, 'bronze.brz_fx_rates',                                                    count(*) from {{ ref('brz_fx_rates') }}
    union all select 'fx_rates', 2, 'silver.stg_fx_rates',                                                    count(*) from {{ ref('stg_fx_rates') }}
    union all select 'fx_rates', 3, 'silver.int_fx_daily (calendar days x currency)',                         count(*) from {{ ref('int_fx_daily') }}
    union all select 'fx_rates', 4, 'silver.int_fx_daily where is_published',                                 count(*) from {{ ref('int_fx_daily') }} where is_published
)

select
    extract,
    stage,
    model,
    n                                                           as rows,
    n - lag(n) over (partition by extract order by stage)       as delta_vs_previous
from counts
order by extract, stage
