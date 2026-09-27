# Timestamp parsing coverage and Bogota date shifts

Generated 2026-09-27 01:07 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_09_timestamp_parsing

Source: `analyses/profiling/dq_09_timestamp_parsing.sql` - 4 row(s)

| col                           | n_rows | raw_not_null | parsed_not_null | parse_failures | min_ts_utc          | max_ts_utc          | rows_day_shifts_in_bogota | rows_month_shifts_in_bogota |
|-------------------------------|--------|--------------|-----------------|----------------|---------------------|---------------------|---------------------------|-----------------------------|
| applications_cdc.event_at_utc | 128197 | 128197       | 128197          | 0              | 2025-01-01 00:00:34 | 2026-07-01 19:15:43 | 26860                     | 889                         |
| customers.created_at          | 30000  | 30000        | 30000           | 0              | 2022-07-17 00:00:00 | 2025-01-01 00:00:00 | 30000                     | 991                         |
| loans.disbursed_at_utc        | 28075  | 28075        | 28075           | 0              | 2025-01-02 11:08:45 | 2026-06-30 23:45:27 | 5900                      | 171                         |
| payments.paid_at_utc          | 112339 | 112339       | 112339          | 0              | 2025-01-27 22:37:00 | 2026-07-01 10:57:00 | 24393                     | 766                         |
