# CDC resolution — applications in final state

Generated 2026-09-27 01:22 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_10_cdc_resolution

Source: `analyses/profiling/dq_10_cdc_resolution.sql` - 15 row(s)

| seq | metric                                                | value                    |
|-----|-------------------------------------------------------|--------------------------|
| 1   | applications in CDC (all)                             | 60000                    |
| 2   | deleted (A3)                                          | 941                      |
| 3   | valid                                                 | 59059                    |
| 4   | valid and APPROVED                                    | 33007                    |
| 5   | valid and REJECTED                                    | 26052                    |
| 6   | valid still CREATED (no decision)                     | 0                        |
| 7   | global approval rate (approved / valid)               | 55.8882 %                |
| 8   | final status differs if ordered by ingest time (F6)   | 54                       |
| 9   |   of which valid                                      | 54                       |
| 10  | valid applications with no real customer (F4 residue) | 3                        |
| 11  | applications whose last event is the delete           | 941                      |
| 12  | events per application: min / avg / max               | 2 / 2.02 / 4             |
| 13  | created_date range (Bogotá)                           | 2024-12-31 .. 2026-06-29 |
| 14  | valid applications by currency                        | BRL=23944, COP=35115     |
| 15  | approval rate by currency                             | BRL=55.91%, COP=55.87%   |
