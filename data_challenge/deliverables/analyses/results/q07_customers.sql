-- Q7. How many real people are in the customer master, and how many customer_ids are redundant?
-- Source: silver.dim_customer (A1 identity = document_number) and silver.stg_customers.
select
    (select count(*) from {{ ref('stg_customers') }})                                   as customer_ids,
    (select count(*) from {{ ref('dim_customer') }})                                    as real_people,
    (select count(*) from {{ ref('stg_customers') }})
        - (select count(*) from {{ ref('dim_customer') }})                              as redundant_customer_ids,
    (select count(*) from {{ ref('dim_customer') }} where has_duplicate_ids)            as people_with_2_ids,
    (select count(*) from {{ ref('dim_customer') }} where has_cross_country_ids)        as people_with_ids_in_2_countries,
    (select count(distinct document_number || '|' || country) from {{ ref('stg_customers') }}) as alt_people_document_plus_country,
    (select count(*) from {{ ref('stg_customers') }})
        - (select count(distinct document_number || '|' || country) from {{ ref('stg_customers') }}) as alt_redundant_document_plus_country
