# Loans, FX fill and GMV in USD

Generated 2026-09-27 01:42 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_13_loans_gmv

Source: `analyses/profiling/dq_13_loans_gmv.sql` - 19 row(s)

| seq | metric                                               | value                                                                                                                                                                          |
|-----|------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | loans delivered                                      | 28075                                                                                                                                                                          |
| 2   | excluded, by reason                                  | NO_APPLICATION=120                                                                                                                                                             |
| 3   | valid loans (Q2)                                     | 27955                                                                                                                                                                          |
| 4   | total GMV in USD (Q2)                                | 8,780,942.16                                                                                                                                                                   |
| 5   | GMV USD by currency                                  | BRL=3,514,482.19, COP=5,266,459.97                                                                                                                                             |
| 6   | loans by currency                                    | BRL=11349, COP=16606                                                                                                                                                           |
| 7   | cohort 2026-01: loans (Q3)                           | 1540                                                                                                                                                                           |
| 8   | cohort 2026-01: GMV USD (Q3)                         | 473,272.15                                                                                                                                                                     |
| 9   | cohort 2026-01 if UTC month were used (loans)        | 1541                                                                                                                                                                           |
| 10  | loans disbursed on a day with no published rate      | 8223                                                                                                                                                                           |
| 11  |   share of valid loans                               | 29.42 %                                                                                                                                                                        |
| 12  | max FX staleness used (days)                         | 3                                                                                                                                                                              |
| 13  | loans matched to a merchant version at disbursement  | 27955                                                                                                                                                                          |
| 14  | loans on UNKNOWN-category versions                   | 237                                                                                                                                                                            |
| 15  | disbursement date range (Bogotá)                     | 2025-01-02 .. 2026-06-30                                                                                                                                                       |
| 16  | days application -> disbursement: min / median / max | 0 / 4.0 / 7                                                                                                                                                                    |
| 17  | top 5 merchants by GMV USD (Q6 preview)              | 1607 BR EDUCATION: 2,062,698 (23.49%) | 1397 CO HEALTH: 683,302 (7.78%) | 1664 CO HEALTH: 379,018 (4.32%) | 1030 CO FASHION: 206,932 (2.36%) | 1286 CO TRAVEL: 148,238 (1.69%) |
| 18  | top 1 / top 5 / top 20 share of GMV                  | 23.49% / 39.63% / 53.86%                                                                                                                                                       |
| 19  | merchants with at least one valid loan               | 698                                                                                                                                                                            |
