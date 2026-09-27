-- Business test (DMBOK: consistency). Validity ranges of the same merchant must not overlap,
-- otherwise a point-in-time join (category as of the event date) returns two rows and
-- double-counts GMV and applications for that merchant.
{{ config(meta = {'dq_dimension': 'consistency'}) }}

select
    a.merchant_id,
    a.valid_from   as a_valid_from,
    a.valid_to     as a_valid_to,
    b.valid_from   as b_valid_from,
    b.valid_to     as b_valid_to
from {{ ref('dim_merchant') }} a
join {{ ref('dim_merchant') }} b
  on  a.merchant_id = b.merchant_id
  and a.merchant_sk < b.merchant_sk
  and a.valid_from <= b.valid_to_effective
  and b.valid_from <= a.valid_to_effective
