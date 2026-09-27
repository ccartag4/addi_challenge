-- Silver / intermediate. Grain: one CDC event (same as staging), enriched with the ordering
-- and per-application flags that fct_application needs. Nothing is filtered here, so every
-- rule can be audited event by event.
--
--   rn_event_desc   1 = the application's latest version by business time (A2):
--                   event time, then ingest time, then I < U < D, then real customer before
--                   placeholder (resolves the same-instant twins of F4)
--   rn_ingest_desc  1 = latest by ingest time; disagreement with rn_event_desc is F6
--   rn_event_asc    1 = the application's first event (creation)
--   resolved_customer_id  the only real customer seen on the application (A4)
--   application_deleted   any D event on the application (A3)
with events as (
    select * from {{ ref('stg_applications_cdc') }}
)

select
    *,
    row_number() over (
        partition by application_id
        order by event_at_utc desc, ingested_at_utc desc, cdc_op_rank desc, is_placeholder_customer asc
    )                                                               as rn_event_desc,
    row_number() over (
        partition by application_id
        order by ingested_at_utc desc, event_at_utc desc, cdc_op_rank desc, is_placeholder_customer asc
    )                                                               as rn_ingest_desc,
    row_number() over (
        partition by application_id
        order by event_at_utc asc, ingested_at_utc asc, cdc_op_rank asc, is_placeholder_customer asc
    )                                                               as rn_event_asc,
    max(customer_id) over (partition by application_id)             as resolved_customer_id,
    bool_or(cdc_op = 'D') over (partition by application_id)        as application_deleted,
    count(*) over (partition by application_id)                     as n_events
from events
