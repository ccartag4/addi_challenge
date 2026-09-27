-- DQ profiling 06 — FX rates: completeness of the daily calendar per currency.
-- The provider publishes on business days only; every missing day must be filled before
-- converting a disbursement that happened on a weekend or holiday.
with fx as (
    select cast(rate_date as date) as d, currency, try_cast(units_per_usd as double) as rate
    from {{ ref('brz_fx_rates') }}
),
bounds as (select min(d) as d_min, max(d) as d_max from fx),
calendar as (
    select cast(unnest(generate_series(d_min, d_max, interval 1 day)) as date) as d
    from bounds
),
grid as (
    select c.d, x.currency
    from calendar c
    cross join (select distinct currency from fx) x
),
missing as (
    select g.d, g.currency
    from grid g
    left join fx on fx.d = g.d and fx.currency = g.currency
    where fx.d is null
)
select
    f.currency,
    count(*)                                                   as published_days,
    min(f.d)                                                   as first_date,
    max(f.d)                                                   as last_date,
    (select count(*) from missing m where m.currency = f.currency)                                   as missing_days,
    (select count(*) from missing m where m.currency = f.currency and dayofweek(m.d) in (0, 6))      as missing_weekend_days,
    (select count(*) from missing m where m.currency = f.currency and dayofweek(m.d) not in (0, 6))  as missing_weekday_days,
    (select string_agg(m.d::varchar, ', ' order by m.d) from missing m
      where m.currency = f.currency and dayofweek(m.d) not in (0, 6))                                as missing_weekday_dates,
    round(min(f.rate), 4)                                      as min_rate,
    round(max(f.rate), 4)                                      as max_rate,
    sum(case when f.rate is null or f.rate <= 0 then 1 else 0 end) as invalid_rates
from fx f
group by f.currency
order by f.currency
