-- Bronze: 1:1 copy of the raw extract. No casting, no filtering, no deduplication.
-- Grain: one row per (rate_date, currency) as delivered.
select
    *,
    'raw_fx_rates.csv'                                                  as _brz_source_file,
    cast('{{ run_started_at.strftime("%Y-%m-%d %H:%M:%S") }}' as timestamp) as _brz_built_at
from {{ source('raw', 'raw_fx_rates') }}
