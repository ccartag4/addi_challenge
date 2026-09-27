-- Business test (DMBOK: completeness / integrity). The delinquency snapshot must contain every
-- valid loan exactly once, including fully settled ones (balance 0): PAR30's denominator is
-- the whole live portfolio, and a missing loan would silently shrink it.
{{ config(meta = {'dq_dimension': 'completeness'}) }}

select loan_id, 'missing_in_snapshot' as problem
from {{ ref('fct_loan') }}
where loan_id not in (select loan_id from {{ ref('dm_loan_delinquency_snapshot') }})

union all

select loan_id, 'not_a_valid_loan' as problem
from {{ ref('dm_loan_delinquency_snapshot') }}
where loan_id not in (select loan_id from {{ ref('fct_loan') }})
