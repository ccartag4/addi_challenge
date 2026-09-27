-- Silver / core. Grain: one row per customer_id (technical key), mapping it to the person
-- (document_number) it belongs to. Facts keep the source customer_id; joining through this
-- bridge gives person-level analysis without rewriting keys in the facts.
select
    c.customer_id,
    d.person_sk,
    c.document_number,
    c.country                                   as customer_country,
    c.created_date                              as customer_created_date,
    (c.customer_id = d.latest_customer_id)      as is_person_latest_id,
    d.n_customer_ids                            as person_n_customer_ids
from {{ ref('stg_customers') }} c
join {{ ref('dim_customer') }} d using (document_number)
