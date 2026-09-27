-- DQ profiling 07 — Customers: one person vs one customer_id, and free-text hygiene.
with c as (
    select * exclude (_brz_source_file, _brz_built_at) from {{ ref('brz_customers') }}
),
docs as (
    select
        document_number,
        count(*)                              as n_ids,
        count(distinct country)               as n_countries,
        count(distinct birth_year)            as n_birth_years,
        count(distinct lower(trim(email)))    as n_emails
    from c
    group by 1
),
multi as (select * from docs where n_ids > 1),
cdc_customers as (
    select distinct customer_id from {{ ref('brz_applications_cdc') }}
)
select * from (values
    ( 1, 'rows',                                                    (select count(*) from c)::varchar),
    ( 2, 'distinct customer_id',                                    (select count(distinct customer_id) from c)::varchar),
    ( 3, 'distinct document_number',                                (select count(distinct document_number) from c)::varchar),
    ( 4, 'redundant customer_ids (rows - distinct documents)',      (select count(*) - count(distinct document_number) from c)::varchar),
    ( 5, 'documents held by >1 customer_id',                        (select count(*) from multi)::varchar),
    ( 6, '  of which spanning >1 country',                          (select count(*) from multi where n_countries > 1)::varchar),
    ( 7, '  of which with >1 birth_year',                           (select count(*) from multi where n_birth_years > 1)::varchar),
    ( 8, '  of which sharing one normalized email',                 (select count(*) from multi where n_emails = 1)::varchar),
    ( 9, 'document_number shapes',                                  (select string_agg(shape || ' x' || n, ', ' order by n desc)
                                                                     from (select regexp_replace(document_number, '\d', '9', 'g') shape, count(*) n from c group by 1))),
    (10, 'country values',                                          (select string_agg(country || '=' || n, ', ' order by country)
                                                                     from (select country, count(*) n from c group by 1))),
    (11, 'monthly_income non-numeric shapes (top 6)',               (select string_agg(shape || ' x' || n, ', ' order by n desc)
                                                                     from (select regexp_replace(monthly_income, '\d', '9', 'g') shape, count(*) n
                                                                           from c where monthly_income is null or not regexp_matches(monthly_income, '^\d+(\.\d+)?$')
                                                                           group by 1 order by n desc limit 6))),
    (12, 'monthly_income = -1',                                     (select count(*) from c where monthly_income = '-1')::varchar),
    (13, 'monthly_income null',                                     (select count(*) from c where monthly_income is null)::varchar),
    (14, 'birth_year min .. max',                                   (select min(birth_year) || ' .. ' || max(birth_year) from c)),
    (15, 'birth_year = 1900 (placeholder?)',                        (select count(*) from c where birth_year = '1900')::varchar),
    (16, 'distinct city raw',                                       (select count(distinct city) from c)::varchar),
    (17, 'distinct city normalized (lower, trim, no accents)',      (select count(distinct lower(trim(strip_accents(city)))) from c)::varchar),
    (18, 'emails not already lower(trim(email))',                   (select count(*) from c where email <> lower(trim(email)))::varchar),
    (19, 'customer_ids referenced by the CDC but missing from master', (select count(*) from cdc_customers k where not exists (select 1 from c where c.customer_id = k.customer_id))::varchar),
    (20, 'CDC rows pointing to those missing customer_ids',         (select count(*) from {{ ref('brz_applications_cdc') }} a where not exists (select 1 from c where c.customer_id = a.customer_id))::varchar)
) t(seq, metric, value)
order by seq
