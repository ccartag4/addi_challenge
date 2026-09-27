-- DQ profiling 10 — Timeliness / Validity: what the CDC resolution (A2, A3, A4) produced.
-- Also yields the figures for business question 1.
with a as (
    select * from {{ ref('fct_application') }}
)
select * from (values
    ( 1, 'applications in CDC (all)',                          (select count(*) from a)::varchar),
    ( 2, 'deleted (A3)',                                       (select count(*) from a where is_deleted)::varchar),
    ( 3, 'valid',                                              (select count(*) from a where is_valid)::varchar),
    ( 4, 'valid and APPROVED',                                 (select count(*) from a where is_approved)::varchar),
    ( 5, 'valid and REJECTED',                                 (select count(*) from a where is_valid and final_status = 'REJECTED')::varchar),
    ( 6, 'valid still CREATED (no decision)',                  (select count(*) from a where is_valid and final_status = 'CREATED')::varchar),
    ( 7, 'global approval rate (approved / valid)',            (select round(100.0 * count(*) filter (where is_approved) / count(*) filter (where is_valid), 4)::varchar || ' %' from a)),
    ( 8, 'final status differs if ordered by ingest time (F6)', (select count(*) from a where is_out_of_order)::varchar),
    ( 9, '  of which valid',                                   (select count(*) from a where is_out_of_order and is_valid)::varchar),
    (10, 'valid applications with no real customer (F4 residue)', (select count(*) from a where is_valid and has_unresolved_customer)::varchar),
    (11, 'applications whose last event is the delete',        (select count(*) from a where last_cdc_op = 'D')::varchar),
    (12, 'events per application: min / avg / max',            (select min(n_events) || ' / ' || round(avg(n_events), 2) || ' / ' || max(n_events) from a)),
    (13, 'created_date range (Bogotá)',                        (select min(created_date) || ' .. ' || max(created_date) from a)),
    (14, 'valid applications by currency',                     (select string_agg(currency || '=' || n, ', ' order by currency) from (select currency, count(*) n from a where is_valid group by 1))),
    (15, 'approval rate by currency',                          (select string_agg(currency || '=' || r || '%', ', ' order by currency) from (select currency, round(100.0 * count(*) filter (where is_approved) / count(*), 2) r from a where is_valid group by 1)))
) t(seq, metric, value)
order by seq
