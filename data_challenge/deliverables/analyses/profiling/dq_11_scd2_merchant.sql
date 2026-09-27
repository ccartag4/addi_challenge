-- DQ profiling 11 — Consistency: what the SCD2 merchant dimension looks like, and how much the
-- "category as of the event date" rule (A14) matters versus using the current category.
with d as (
    select * from {{ ref('dim_merchant') }}
),
apps as (
    select a.application_id, a.merchant_id, a.created_date, a.is_approved,
           m.category   as category_as_of_event,
           c.category   as category_current
    from {{ ref('fct_application') }} a
    join d m on m.merchant_id = a.merchant_id
            and a.created_date between m.valid_from and m.valid_to_effective
    join d c on c.merchant_id = a.merchant_id and c.is_current
    where a.is_valid
)
select * from (values
    ( 1, 'version rows',                                            (select count(*) from d)::varchar),
    ( 2, 'distinct merchants',                                      (select count(distinct merchant_id) from d)::varchar),
    ( 3, 'current rows (must equal merchants)',                     (select count(*) from d where is_current)::varchar),
    ( 4, 'merchants with 2 versions',                               (select count(*) from (select merchant_id from d group by 1 having count(*) = 2))::varchar),
    ( 5, 'versions where the category changed',                     (select count(*) from d where category_changed)::varchar),
    ( 6, 'versions where only the name casing changed',             (select count(*) from d where version_number > 1 and not category_changed)::varchar),
    ( 7, 'earliest / latest valid_from',                            (select min(valid_from) || ' / ' || max(valid_from) from d)),
    ( 8, 'closed versions: min / max length in days',               (select min(valid_to - valid_from + 1) || ' / ' || max(valid_to - valid_from + 1) from d where valid_to is not null)),
    ( 9, 'valid applications matched to a version',                 (select count(*) from apps)::varchar),
    (10, 'applications whose as-of category <> current category',   (select count(*) from apps where category_as_of_event <> category_current)::varchar),
    (11, '  share of valid applications',                           (select round(100.0 * count(*) filter (where category_as_of_event <> category_current) / count(*), 2)::varchar || ' %' from apps)),
    (12, 'current category mix (merchants)',                        (select string_agg(category || '=' || n, ', ' order by category) from (select category, count(*) n from d where is_current group by 1))),
    (13, 'merchant 1607 (largest by GMV in profiling): versions',   (select string_agg(version_number || ':' || category || ' ' || country || ' from ' || valid_from, ' | ' order by version_number) from d where merchant_id = 1607))
) t(seq, metric, value)
order by seq
