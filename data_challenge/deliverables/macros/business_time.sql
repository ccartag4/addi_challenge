{#-
    Business-time helpers (assumption A6). Operations close in America/Bogota; every business
    date derives from a UTC timestamp converted to that zone. The zone is a project var so it
    is set once.

    to_business_ts(utc_ts)   naive UTC timestamp -> naive local timestamp in business_tz
    to_business_date(utc_ts) naive UTC timestamp -> local DATE in business_tz

    Mechanics: timezone('UTC', ts) tags the naive timestamp as UTC (TIMESTAMPTZ);
    timezone(business_tz, tstz) then renders it as local wall-clock time (naive TIMESTAMP).
    Same idiom as SQL's `ts AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota'`.
-#}
{% macro to_business_ts(utc_ts) -%}
    timezone('{{ var("business_tz") }}', timezone('UTC', {{ utc_ts }}))
{%- endmacro %}

{% macro to_business_date(utc_ts) -%}
    cast({{ to_business_ts(utc_ts) }} as date)
{%- endmacro %}
