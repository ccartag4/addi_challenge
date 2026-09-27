-- DQ profiling 02 — Uniqueness: exact duplicate rows and duplicate business keys per extract.
--   exact_duplicate_rows : identical rows (dump reprocessing, per the data dictionary).
--   key_duplicate_rows   : rows still sharing the declared key after exact duplicates are
--                          removed (same key, different content: needs a rule, not a DISTINCT).
{% set tables = {
    'applications_cdc':  ['application_id', 'event_at_utc', '_op'],
    'loans':             ['loan_id'],
    'installments':      ['loan_id', 'installment_number'],
    'payments':          ['payment_id'],
    'customers':         ['customer_id'],
    'merchants_history': ['merchant_id', 'valid_from'],
    'fx_rates':          ['rate_date', 'currency']
} %}

with
{% for tbl, keys in tables.items() %}
d_{{ loop.index }} as (
    select distinct * exclude (_brz_source_file, _brz_built_at)
    from {{ ref('brz_' ~ tbl) }}
),
{% endfor %}
final as (
{% for tbl, keys in tables.items() %}
    select
        '{{ tbl }}'                                          as extract,
        '{{ keys | join(" + ") }}'                           as declared_key,
        (select count(*) from {{ ref('brz_' ~ tbl) }})       as total_rows,
        (select count(*) from d_{{ loop.index }})            as distinct_rows,
        (select count(*) from {{ ref('brz_' ~ tbl) }})
            - (select count(*) from d_{{ loop.index }})      as exact_duplicate_rows,
        (select count(*) from d_{{ loop.index }})
            - (select count(distinct concat_ws('|', {{ keys | join(', ') }}))
               from d_{{ loop.index }})                      as key_duplicate_rows
    {% if not loop.last %} union all {% endif %}
{% endfor %}
)
select * from final order by extract
