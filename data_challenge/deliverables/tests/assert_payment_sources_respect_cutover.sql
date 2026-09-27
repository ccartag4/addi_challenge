-- Business test (DMBOK: timeliness). The processor migration (data dictionary: legacy_v1
-- through Jun-2025, core_v2 from Jul-2025) must hold in the data. Observed boundary (F18):
-- legacy closes at the Bogotá business day (last payment 2025-06-30 22:03 local), core_v2
-- opens at UTC midnight (first payment 2025-07-01 00:04 UTC). Returns rows on the wrong side.
{{ config(meta = {'dq_dimension': 'timeliness'}) }}

select
    payment_id,
    source_system,
    paid_at_utc,
    paid_date
from {{ ref('stg_payments') }}
where (source_system = 'legacy_v1' and paid_date    >= cast('{{ var("cutover_date") }}' as date))
   or (source_system = 'core_v2'   and paid_at_utc  <  cast('{{ var("cutover_date") }}' as timestamp))
