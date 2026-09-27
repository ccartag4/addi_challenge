-- DQ profiling 08 — Merchant history: how many versions, what changes, and name hygiene.
with m as (
    select * exclude (_brz_source_file, _brz_built_at) from {{ ref('brz_merchants_history') }}
),
per_merchant as (
    select
        merchant_id,
        count(*)                                        as n_versions,
        count(distinct category)                        as n_categories,
        count(distinct country)                         as n_countries,
        count(distinct merchant_name)                   as n_names_raw,
        count(distinct upper(trim(merchant_name)))      as n_names_norm
    from m
    group by 1
),
cdc_merchants  as (select distinct merchant_id from {{ ref('brz_applications_cdc') }}),
loan_merchants as (select distinct merchant_id from {{ ref('brz_loans') }})
select * from (values
    ( 1, 'rows',                                                   (select count(*) from m)::varchar),
    ( 2, 'distinct merchant_id',                                   (select count(distinct merchant_id) from m)::varchar),
    ( 3, 'merchants with 1 version',                               (select count(*) from per_merchant where n_versions = 1)::varchar),
    ( 4, 'merchants with 2 versions',                              (select count(*) from per_merchant where n_versions = 2)::varchar),
    ( 5, 'merchants with 3+ versions',                             (select count(*) from per_merchant where n_versions >= 3)::varchar),
    ( 6, 'merchants whose category changed',                       (select count(*) from per_merchant where n_categories > 1)::varchar),
    ( 7, 'merchants whose country changed',                        (select count(*) from per_merchant where n_countries > 1)::varchar),
    ( 8, 'merchants whose name differs only by case/spaces',       (select count(*) from per_merchant where n_names_raw > n_names_norm)::varchar),
    ( 9, 'merchants whose normalized name really changed',         (select count(*) from per_merchant where n_names_norm > 1)::varchar),
    (10, 'category values',                                        (select string_agg(category || '=' || n, ', ' order by category)
                                                                    from (select category, count(*) n from m group by 1))),
    (11, 'valid_from min .. max',                                  (select min(valid_from) || ' .. ' || max(valid_from) from m)),
    (12, 'merchants in CDC missing from history',                  (select count(*) from cdc_merchants k where not exists (select 1 from m where m.merchant_id = k.merchant_id))::varchar),
    (13, 'merchants in loans missing from history',                (select count(*) from loan_merchants k where not exists (select 1 from m where m.merchant_id = k.merchant_id))::varchar),
    (14, 'merchants in history never used by any application',     (select count(*) from per_merchant p where not exists (select 1 from cdc_merchants k where k.merchant_id = p.merchant_id))::varchar)
) t(seq, metric, value)
order by seq
