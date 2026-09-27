-- Business test (DMBOK: consistency). An SCD2 dimension must expose exactly one current
-- version per merchant; zero would hide the merchant from current reports, two would double
-- its rows in any join.
{{ config(meta = {'dq_dimension': 'consistency'}) }}

select
    merchant_id,
    sum(case when is_current then 1 else 0 end) as current_versions
from {{ ref('dim_merchant') }}
group by merchant_id
having sum(case when is_current then 1 else 0 end) <> 1
