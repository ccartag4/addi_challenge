-- Business test (DMBOK: integrity / completeness). Collapsing customer_ids into people must
-- lose nothing: every customer_id in staging maps to exactly one person and vice versa.
-- Returns the ids missing on either side.
{{ config(meta = {'dq_dimension': 'integrity'}) }}

select customer_id, 'missing_from_bridge' as problem
from {{ ref('stg_customers') }}
where customer_id not in (select customer_id from {{ ref('bridge_customer_person') }})

union all

select customer_id, 'not_in_staging' as problem
from {{ ref('bridge_customer_person') }}
where customer_id not in (select customer_id from {{ ref('stg_customers') }})
