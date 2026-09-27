{#-
    parse_utc_ts(col)

    Parses the three timestamp shapes found in the raw extracts (finding F1) into a naive
    TIMESTAMP that represents UTC:

      '2025-05-27 00:54:06'      plain
      '2025-05-27T00:54:06Z'     ISO 8601 with Z
      '1748306046000'            Unix epoch in milliseconds (13 digits)

    Anything else yields NULL so a not_null test on the parsed column catches new shapes.

    Why epoch_ms() and not to_timestamp(): to_timestamp() returns TIMESTAMP WITH TIME ZONE and
    casting that to TIMESTAMP applies the session time zone (the machine's local zone), which
    would silently shift epoch values by -5h on a Bogotá laptop. epoch_ms() returns a naive
    UTC timestamp directly. strptime() without %z also returns a naive timestamp.
-#}
{% macro parse_utc_ts(col) -%}
    case
        when {{ col }} is null or trim({{ col }}) = '' then null
        when regexp_matches({{ col }}, '^\d{13}$')
            then epoch_ms(cast({{ col }} as bigint))
        when regexp_matches({{ col }}, '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
            then strptime({{ col }}, '%Y-%m-%dT%H:%M:%SZ')
        when regexp_matches({{ col }}, '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
            then strptime({{ col }}, '%Y-%m-%d %H:%M:%S')
        else null
    end
{%- endmacro %}
