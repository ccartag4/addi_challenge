-- Silver / intermediate. Grain: one row per calendar day x currency, from the first published
-- rate to the later of the last published rate and the snapshot date.
--
-- The provider publishes on business days only (F12: 170 weekend days and 6 holidays missing
-- per currency). Each calendar day carries the last published rate on or before it (A7,
-- forward fill), with the source date and staleness kept so the fill is auditable.
with rates as (
    select rate_date, currency, units_per_usd
    from {{ ref('stg_fx_rates') }}
),

bounds as (
    select
        min(rate_date)                                                          as d_min,
        greatest(max(rate_date), cast('{{ var("snapshot_date") }}' as date))    as d_max
    from rates
),

calendar as (
    select cast(unnest(generate_series(d_min, d_max, interval 1 day)) as date) as rate_date
    from bounds
),

currencies as (
    select distinct currency from rates
),

grid as (
    select c.rate_date, x.currency
    from calendar c
    cross join currencies x
),

joined as (
    select
        g.rate_date,
        g.currency,
        r.units_per_usd                                             as published_units_per_usd,
        case when r.rate_date is not null then g.rate_date end      as published_on
    from grid g
    left join rates r
      on r.rate_date = g.rate_date
     and r.currency  = g.currency
)

select
    rate_date,
    currency,
    last_value(published_units_per_usd ignore nulls) over w         as units_per_usd,
    last_value(published_on ignore nulls) over w                    as rate_source_date,
    (published_units_per_usd is not null)                           as is_published,
    rate_date - last_value(published_on ignore nulls) over w        as days_stale
from joined
window w as (
    partition by currency
    order by rate_date
    rows between unbounded preceding and current row
)
