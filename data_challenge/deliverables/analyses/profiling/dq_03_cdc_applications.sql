-- DQ profiling 03 — Applications CDC: operations, statuses, deletes and same-instant events.
-- Works on exact-deduplicated rows so dump reprocessing does not inflate the counts.
with cdc as (
    select distinct * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_applications_cdc') }}
),
deleted as (
    select distinct application_id from cdc where _op = 'D'
),
same_instant as (
    select application_id, event_at_utc
    from cdc
    group by 1, 2
    having count(*) > 1
),
multi_customer as (
    select application_id from cdc group by 1 having count(distinct customer_id) > 1
),
multi_merchant as (
    select application_id from cdc group by 1 having count(distinct merchant_id) > 1
)
select * from (values
    ( 1, 'rows after exact dedup',                          (select count(*) from cdc)::varchar),
    ( 2, 'distinct application_id',                         (select count(distinct application_id) from cdc)::varchar),
    ( 3, 'rows with _op = I',                               (select count(*) from cdc where _op = 'I')::varchar),
    ( 4, 'rows with _op = U',                               (select count(*) from cdc where _op = 'U')::varchar),
    ( 5, 'rows with _op = D',                               (select count(*) from cdc where _op = 'D')::varchar),
    ( 6, 'other _op values',                                (select count(*) from cdc where _op not in ('I','U','D') or _op is null)::varchar),
    ( 7, 'applications with at least one D event',          (select count(*) from deleted)::varchar),
    ( 8, 'rows with status CREATED',                        (select count(*) from cdc where status = 'CREATED')::varchar),
    ( 9, 'rows with status APPROVED',                       (select count(*) from cdc where status = 'APPROVED')::varchar),
    (10, 'rows with status REJECTED',                       (select count(*) from cdc where status = 'REJECTED')::varchar),
    (11, 'rows with other / null status',                   (select count(*) from cdc where status not in ('CREATED','APPROVED','REJECTED') or status is null)::varchar),
    (12, 'currency values',                                 (select string_agg(distinct currency, ', ') from cdc)),
    (13, '(application_id, event_at_utc) pairs with >1 row', (select count(*) from same_instant)::varchar),
    (14, 'APPROVED rows with null approved_amount',         (select count(*) from cdc where status = 'APPROVED' and approved_amount is null)::varchar),
    (15, 'rows with approved_amount > requested_amount',    (select count(*) from cdc where try_cast(approved_amount as double) > try_cast(requested_amount as double))::varchar),
    (16, 'rows with requested_amount <= 0 or null',         (select count(*) from cdc where coalesce(try_cast(requested_amount as double), 0) <= 0)::varchar),
    (17, 'applications with >1 distinct customer_id',       (select count(*) from multi_customer)::varchar),
    (18, 'applications with >1 distinct merchant_id',       (select count(*) from multi_merchant)::varchar),
    (19, 'rows with null customer_id or merchant_id',       (select count(*) from cdc where customer_id is null or merchant_id is null)::varchar)
) t(seq, metric, value)
order by seq
