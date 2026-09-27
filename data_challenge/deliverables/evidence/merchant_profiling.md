# Merchant history profiling (with NULL counts)

Generated 2026-09-27 01:29 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_08_merchants

Source: `analyses/profiling/dq_08_merchants.sql` - 19 row(s)

| seq | metric                                                 | value                                                                                          |
|-----|--------------------------------------------------------|------------------------------------------------------------------------------------------------|
| 1   | rows                                                   | 862                                                                                            |
| 2   | distinct merchant_id                                   | 700                                                                                            |
| 3   | merchants with 1 version                               | 538                                                                                            |
| 4   | merchants with 2 versions                              | 162                                                                                            |
| 5   | merchants with 3+ versions                             | 0                                                                                              |
| 6   | merchants whose category changed                       | 157                                                                                            |
| 7   | merchants whose country changed                        | 0                                                                                              |
| 8   | merchants whose name differs only by case/spaces       | 72                                                                                             |
| 9   | merchants whose normalized name really changed         | 0                                                                                              |
| 10  | category values                                        | EDUCATION=116, ELECTRONICS=121, FASHION=125, HEALTH=126, HOME=129, MOTORCYCLES=117, TRAVEL=112 |
| 11  | valid_from min .. max                                  | 2023-02-03 .. 2026-04-21                                                                       |
| 12  | merchants in CDC missing from history                  | 0                                                                                              |
| 13  | merchants in loans missing from history                | 0                                                                                              |
| 14  | merchants in history never used by any application     | 0                                                                                              |
| 15  | rows with null merchant_name                           | 0                                                                                              |
| 16  | rows with null category                                | 16                                                                                             |
| 17  | rows with null country                                 | 0                                                                                              |
| 18  | null-category rows that are a merchant's only version  | 11                                                                                             |
| 19  | null-category rows with an earlier categorised version | 5                                                                                              |
