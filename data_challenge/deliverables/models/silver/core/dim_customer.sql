-- Silver / core. Grain: one row per real person = one document_number (A1).
-- 30,000 customer_ids collapse to 29,093 people (F13). Attributes come from the person's
-- most recently created customer record (A18); counts and conflict flags describe all of the
-- person's records so nothing about the collapse is hidden. customer_id -> person mapping
-- lives in bridge_customer_person.
with customers as (
    select * from {{ ref('stg_customers') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by document_number
            order by created_at_utc desc, ingested_at_utc desc, customer_id desc
        ) as rn_latest
    from customers
),

per_person as (
    select
        document_number,
        count(*)                                        as n_customer_ids,
        count(distinct country)                         as n_countries,
        count(distinct birth_year)                      as n_birth_years,     -- NULLs ignored
        min(created_date)                               as first_created_date,
        max(created_date)                               as last_created_date,
        string_agg(cast(customer_id as varchar), ',' order by customer_id) as customer_ids
    from customers
    group by document_number
),

latest as (
    select * from ranked where rn_latest = 1
)

select
    {{ dbt_utils.generate_surrogate_key(['l.document_number']) }}   as person_sk,
    l.document_number,
    l.customer_id                                                   as latest_customer_id,
    l.country,
    coalesce(c.city_name, l.city_raw)                               as city,
    l.city_key,
    l.email,
    l.birth_year,
    l.monthly_income,
    p.first_created_date,
    p.last_created_date,
    p.n_customer_ids,
    p.customer_ids,
    (p.n_customer_ids > 1)                                          as has_duplicate_ids,          -- F13
    (p.n_countries > 1)                                             as has_cross_country_ids,      -- F13: 346 people
    (p.n_birth_years > 1)                                           as has_conflicting_birth_year  -- F13: 886 people
from latest l
join per_person p using (document_number)
left join {{ ref('city_canonical') }} c on c.city_key = l.city_key
