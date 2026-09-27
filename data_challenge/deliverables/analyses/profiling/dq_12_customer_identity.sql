-- DQ profiling 12 — Uniqueness: customer_ids vs real people (A1, F13). Yields the figures for
-- business question 7, plus the alternative count under document_number + country.
with d as (
    select * from {{ ref('dim_customer') }}
),
s as (
    select * from {{ ref('stg_customers') }}
)
select * from (values
    ( 1, 'customer_ids in the master',                                  (select count(*) from s)::varchar),
    ( 2, 'real people (distinct document_number, A1)',                  (select count(*) from d)::varchar),
    ( 3, 'redundant customer_ids (ids - people)',                       (select (select count(*) from s) - (select count(*) from d))::varchar),
    ( 4, 'people holding >1 customer_id',                               (select count(*) from d where has_duplicate_ids)::varchar),
    ( 5, 'max customer_ids for one person',                             (select max(n_customer_ids) from d)::varchar),
    ( 6, 'people whose ids span two countries',                         (select count(*) from d where has_cross_country_ids)::varchar),
    ( 7, 'people whose ids carry different birth years',                (select count(*) from d where has_conflicting_birth_year)::varchar),
    ( 8, 'alternative: people if identity were document + country',     (select count(distinct document_number || '|' || country) from s)::varchar),
    ( 9, 'alternative: redundant ids under document + country',         (select (select count(*) from s) - (select count(distinct document_number || '|' || country) from s))::varchar),
    (10, 'people by country (latest record)',                           (select string_agg(country || '=' || n, ', ' order by country) from (select country, count(*) n from d group by 1))),
    (11, 'people by canonical city',                                    (select string_agg(city || '=' || n, ', ' order by n desc) from (select city, count(*) n from d group by 1))),
    (12, 'people with city not in the canonical seed',                  (select count(*) from d where city_key not in (select city_key from {{ ref('city_canonical') }}))::varchar),
    (13, 'people with null birth_year / null income (A16)',             (select count(*) filter (where birth_year is null) || ' / ' || count(*) filter (where monthly_income is null) from d)),
    (14, 'first_created_date range',                                    (select min(first_created_date) || ' .. ' || max(first_created_date) from d))
) t(seq, metric, value)
order by seq
