{#-
    Override of dbt's default schema naming.

    By default dbt concatenates the target schema and the custom schema, which in DuckDB
    produces `main_bronze`, `main_silver`, `main_gold`. This override uses the custom schema
    name as-is, so the warehouse exposes exactly `bronze`, `silver`, `gold` and `dq_audit`.
    Models without a custom schema fall back to the target schema (`main`).
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
