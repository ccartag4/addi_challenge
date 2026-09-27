# Customer identity - customer_ids vs real people

Generated 2026-09-27 01:36 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_12_customer_identity

Source: `analyses/profiling/dq_12_customer_identity.sql` - 14 row(s)

| seq | metric                                                  | value                                                                                                                                                  |
|-----|---------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | customer_ids in the master                              | 30000                                                                                                                                                  |
| 2   | real people (distinct document_number, A1)              | 29093                                                                                                                                                  |
| 3   | redundant customer_ids (ids - people)                   | 907                                                                                                                                                    |
| 4   | people holding >1 customer_id                           | 907                                                                                                                                                    |
| 5   | max customer_ids for one person                         | 2                                                                                                                                                      |
| 6   | people whose ids span two countries                     | 346                                                                                                                                                    |
| 7   | people whose ids carry different birth years            | 884                                                                                                                                                    |
| 8   | alternative: people if identity were document + country | 29439                                                                                                                                                  |
| 9   | alternative: redundant ids under document + country     | 561                                                                                                                                                    |
| 10  | people by country (latest record)                       | BR=8151, CO=20942                                                                                                                                      |
| 11  | people by canonical city                                | Bogotá D.C.=7760, Medellín=5229, São Paulo=4196, Cali=2715, Cartagena=2626, Barranquilla=2612, Rio de Janeiro=1334, Curitiba=1331, Belo Horizonte=1290 |
| 12  | people with city not in the canonical seed              | 0                                                                                                                                                      |
| 13  | people with null birth_year / null income (A16)         | 63 / 2292                                                                                                                                              |
| 14  | first_created_date range                                | 2022-07-17 .. 2025-01-01                                                                                                                               |
