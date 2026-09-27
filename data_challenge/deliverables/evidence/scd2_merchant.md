# SCD2 merchant dimension - verification

Generated 2026-09-27 01:29 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_11_scd2_merchant

Source: `analyses/profiling/dq_11_scd2_merchant.sql` - 13 row(s)

| seq | metric                                                | value                                                                                                   |
|-----|-------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| 1   | version rows                                          | 862                                                                                                     |
| 2   | distinct merchants                                    | 700                                                                                                     |
| 3   | current rows (must equal merchants)                   | 700                                                                                                     |
| 4   | merchants with 2 versions                             | 162                                                                                                     |
| 5   | versions where the category changed                   | 157                                                                                                     |
| 6   | versions where only the name casing changed           | 5                                                                                                       |
| 7   | earliest / latest valid_from                          | 2023-02-03 / 2026-04-21                                                                                 |
| 8   | closed versions: min / max length in days             | 112 / 1100                                                                                              |
| 9   | valid applications matched to a version               | 59059                                                                                                   |
| 10  | applications whose as-of category <> current category | 4822                                                                                                    |
| 11  |   share of valid applications                         | 8.16 %                                                                                                  |
| 12  | current category mix (merchants)                      | EDUCATION=100, ELECTRONICS=93, FASHION=100, HEALTH=103, HOME=106, MOTORCYCLES=95, TRAVEL=92, UNKNOWN=11 |
| 13  | merchant 1607 (largest by GMV in profiling): versions | 1:EDUCATION BR from 2023-03-10                                                                          |
