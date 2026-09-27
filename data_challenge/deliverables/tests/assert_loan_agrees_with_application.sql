-- Business test (DMBOK: consistency). A valid loan is the disbursement of its application:
-- currency and merchant must match, and when the loan carries a real customer it must be the
-- application's resolved customer (A19). Any row here is a join that would mis-assign GMV.
{{ config(meta = {'dq_dimension': 'consistency'}) }}

select
    loan_id,
    application_id,
    currency,       app_currency,
    merchant_id,    app_merchant_id,
    customer_id,    app_customer_id
from {{ ref('int_loan_validated') }}
where is_valid
  and (
        currency    <> app_currency
     or merchant_id <> app_merchant_id
     or (app_customer_id is not null and customer_id <> app_customer_id)
  )
