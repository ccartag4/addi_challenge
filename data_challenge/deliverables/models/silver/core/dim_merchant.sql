-- Silver / core. Grain: one row per merchant version (merchant_id x valid_from), SCD type 2
-- derived from the append-only history (F15).
--
--   valid_from          first day these attributes apply (from source)
--   valid_to            last day they apply = next version's valid_from - 1 day; NULL when current
--   valid_to_effective  same, with 9999-12-31 instead of NULL, for BETWEEN joins
--   is_current          the merchant's latest version
--
-- Category gaps (F17, A17): 16 source versions have no category. When an earlier version of
-- the same merchant has one, it is carried forward (the append did not change the category);
-- when the merchant never had one, the label UNKNOWN is used. category_source keeps the raw
-- value and category_imputation says which rule applied, so nothing is silently invented.
--
-- Point-in-time lookup: join on merchant_id and event_date between valid_from and
-- valid_to_effective. Every event date must land in exactly one version; singular tests
-- assert_dim_merchant_no_overlapping_versions and assert_dim_merchant_one_current_version
-- guarantee that.
with history as (
    select * from {{ ref('stg_merchants_history') }}
),

versions as (
    select
        merchant_id,
        merchant_name,
        merchant_name_key,
        category                                                                as category_source,
        last_value(category ignore nulls) over (
            partition by merchant_id order by valid_from
            rows between unbounded preceding and current row
        )                                                                       as category_carried,
        country,
        valid_from,
        cast(lead(valid_from) over (partition by merchant_id order by valid_from)
             - interval 1 day as date)                                          as valid_to,
        row_number() over (partition by merchant_id order by valid_from)        as version_number,
        count(*)    over (partition by merchant_id)                             as n_versions,
        last_value(merchant_name) over (
            partition by merchant_id order by valid_from
            rows between unbounded preceding and unbounded following
        )                                                                       as merchant_name_current
    from history
),

resolved as (
    select
        *,
        coalesce(category_carried, 'UNKNOWN')                                   as category,
        case
            when category_source is not null            then null
            when category_carried is not null           then 'CARRIED_FORWARD'
            else                                             'UNKNOWN'
        end                                                                     as category_imputation
    from versions
),

with_previous as (
    select
        *,
        lag(category) over (partition by merchant_id order by valid_from)       as previous_category
    from resolved
)

select
    {{ dbt_utils.generate_surrogate_key(['merchant_id', 'valid_from']) }}       as merchant_sk,
    merchant_id,
    version_number,
    n_versions,
    merchant_name,
    merchant_name_key,
    merchant_name_current,
    category,
    category_source,
    category_imputation,
    previous_category,
    (previous_category is not null and category <> previous_category)          as category_changed,
    country,
    valid_from,
    valid_to,
    coalesce(valid_to, date '9999-12-31')                                       as valid_to_effective,
    (valid_to is null)                                                          as is_current
from with_previous
