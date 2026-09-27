-- Business test (DMBOK: consistency). The arithmetic behind business question 7 must hold:
--   customer_ids in staging = sum of n_customer_ids over people = rows in the bridge
--   redundant ids            = customer_ids - people
-- Returns one row when any of the three counts disagree.
{{ config(meta = {'dq_dimension': 'consistency'}) }}

with counts as (
    select
        (select count(*)             from {{ ref('stg_customers') }})          as customer_ids,
        (select count(*)             from {{ ref('dim_customer') }})           as people,
        (select sum(n_customer_ids)  from {{ ref('dim_customer') }})           as ids_summed_over_people,
        (select count(*)             from {{ ref('bridge_customer_person') }}) as bridge_rows
)

select *
from counts
where customer_ids <> ids_summed_over_people
   or customer_ids <> bridge_rows
   or people > customer_ids
