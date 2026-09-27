{#-
    Text hygiene helpers (finding F14, F15).

    clean_text(col)     trim, collapse internal whitespace, empty string -> NULL
    normalize_key(col)  clean_text + upper + accents removed: for matching names/cities
                        ('Bogotá D.C.', 'bogota dc' style variants collapse together)
    parse_number(col)   strip thousands separators and cast; non-numeric -> NULL
-#}
{% macro clean_text(col) -%}
    nullif(trim(regexp_replace({{ col }}, '\s+', ' ', 'g')), '')
{%- endmacro %}

{% macro normalize_key(col) -%}
    upper(strip_accents({{ clean_text(col) }}))
{%- endmacro %}

{% macro parse_number(col, precision=18, scale=2) -%}
    try_cast(replace(trim({{ col }}), ',', '') as decimal({{ precision }}, {{ scale }}))
{%- endmacro %}
