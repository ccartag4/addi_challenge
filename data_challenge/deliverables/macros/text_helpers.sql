{#-
    Text hygiene helpers (finding F14, F15).

    clean_text(col)     trim, collapse internal whitespace, empty string -> NULL
    normalize_key(col)  upper, accents removed, everything but A-Z0-9 dropped: a matching key,
                        not a display value ('Bogotá D.C.', 'bogota dc' -> 'BOGOTADC';
                        'Comercio 1018 Shop', 'COMERCIO 1018 SHOP' -> 'COMERCIO1018SHOP')
    parse_number(col)   strip thousands separators and cast; non-numeric ('N/A') -> NULL
-#}
{% macro clean_text(col) -%}
    nullif(trim(regexp_replace({{ col }}, '\s+', ' ', 'g')), '')
{%- endmacro %}

{% macro normalize_key(col) -%}
    nullif(regexp_replace(upper(strip_accents({{ col }})), '[^A-Z0-9]', '', 'g'), '')
{%- endmacro %}

{% macro parse_number(col, precision=18, scale=2) -%}
    try_cast(replace(trim({{ col }}), ',', '') as decimal({{ precision }}, {{ scale }}))
{%- endmacro %}
