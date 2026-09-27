-- Silver / core. Grain: one row per application_id, in its final state.
-- Every application in the CDC is present, including deleted ones, with is_valid / is_approved
-- flags: downstream models filter, this model explains. (A2, A3, A4, A14)
with ev as (
    select * from {{ ref('int_application_events') }}
),

latest as (
    select * from ev where rn_event_desc = 1
),

latest_by_ingest as (
    select application_id, status as status_by_ingest_order
    from ev
    where rn_ingest_desc = 1
),

first_event as (
    select application_id, event_at_utc as created_at_utc, event_date as created_date
    from ev
    where rn_event_asc = 1
),

decision as (
    -- latest decision event (approval or rejection) that is not the delete itself
    select application_id, max(event_at_utc) as decided_at_utc
    from ev
    where status in ('APPROVED', 'REJECTED') and cdc_op <> 'D'
    group by 1
)

select
    l.application_id,
    l.resolved_customer_id                                          as customer_id,
    l.merchant_id,
    l.currency,
    l.requested_amount,
    l.approved_amount,
    l.status                                                        as final_status,
    l.application_deleted                                           as is_deleted,
    not l.application_deleted                                       as is_valid,
    (not l.application_deleted and l.status = 'APPROVED')           as is_approved,
    f.created_at_utc,
    f.created_date,
    cast(date_trunc('month', f.created_date) as date)               as created_month,
    d.decided_at_utc,
    {{ to_business_date('d.decided_at_utc') }}                      as decided_date,
    l.event_at_utc                                                  as last_event_at_utc,
    l.ingested_at_utc                                               as last_ingested_at_utc,
    l.cdc_op                                                        as last_cdc_op,
    l.n_events,
    (l.status <> i.status_by_ingest_order)                          as is_out_of_order,          -- F6
    (l.resolved_customer_id is null)                                as has_unresolved_customer   -- F4 residue
from latest l
join first_event      f using (application_id)
join latest_by_ingest i using (application_id)
left join decision    d using (application_id)
