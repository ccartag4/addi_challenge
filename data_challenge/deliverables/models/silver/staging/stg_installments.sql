-- Silver / staging. Grain: loan_id x installment_number, typed.
-- due_date is already a business date in local time (data dictionary): no conversion.
with src as (
    select * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_installments') }}
)

select distinct
    cast(loan_id as bigint)                             as loan_id,
    cast(installment_number as integer)                 as installment_number,
    cast(due_date as date)                              as due_date,
    {{ parse_number('amount_due') }}                    as amount_due
from src
