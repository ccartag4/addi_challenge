-- Q1. How many valid applications and how many approved, in total? Global approval rate.
-- Source: silver.fct_application (A2 final state, A3 deletes excluded).
select
    count(*) filter (where is_valid)                                            as valid_applications,
    count(*) filter (where is_approved)                                         as approved_applications,
    count(*) filter (where is_valid and final_status = 'REJECTED')              as rejected_applications,
    round(100.0 * count(*) filter (where is_approved)
              / count(*) filter (where is_valid), 4)                            as approval_rate_pct,
    count(*) filter (where is_deleted)                                          as deleted_applications_excluded,
    count(*)                                                                    as applications_in_cdc
from {{ ref('fct_application') }}
