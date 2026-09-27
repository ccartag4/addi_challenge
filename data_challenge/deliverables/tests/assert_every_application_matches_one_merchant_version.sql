-- Business test (DMBOK: integrity). The point-in-time join that agg_merchant_monthly relies
-- on (A14: category in effect on the application's creation date) must find exactly one
-- merchant version for every valid application. Zero matches means an event before the
-- merchant's first version; two means overlapping versions.
{{ config(meta = {'dq_dimension': 'integrity'}) }}

with matches as (
    select
        a.application_id,
        count(m.merchant_sk) as n_versions_matched
    from {{ ref('fct_application') }} a
    left join {{ ref('dim_merchant') }} m
      on  m.merchant_id = a.merchant_id
      and a.created_date between m.valid_from and m.valid_to_effective
    where a.is_valid
    group by a.application_id
)

select *
from matches
where n_versions_matched <> 1
