-- Business test (DMBOK: integrity). A CDC-deleted application "did not exist for business
-- purposes" (A3), so no disbursed loan may point at one. Profiling (dq_04 row 7) found 0;
-- this test keeps it that way as new extracts arrive.
{{ config(meta = {'dq_dimension': 'integrity'}) }}

select
    l.loan_id,
    l.application_id
from {{ ref('stg_loans') }} l
join {{ ref('fct_application') }} a using (application_id)
where a.is_deleted
