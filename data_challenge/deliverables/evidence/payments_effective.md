# Payments - from delivered rows to effective payments

Generated 2026-09-27 01:47 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_14_payments_effective

Source: `analyses/profiling/dq_14_payments_effective.sql` - 19 row(s)

| seq | metric                                                        | value                                                  |
|-----|---------------------------------------------------------------|--------------------------------------------------------|
| 1   | payment rows delivered (bronze)                               | 112339                                                 |
| 2   | payment rows after dedup (staging)                            | 110136                                                 |
| 3   | by class                                                      | EFFECTIVE=107554, REVERSAL_ROW=1291, REVERSED_OUT=1291 |
| 4   | voided payments hit by 2 reversal rows (F11)                  | 0                                                      |
| 5   | effective payments on invalid loans                           | 0                                                      |
| 6   | effective payments (fct_payment)                              | 107554                                                 |
| 7   | effective by source                                           | core_v2=87129, legacy_v1=20425                         |
| 8   | effective by method                                           | PSE=37784, CARD=32223, CASH=21320, TRANSFER=16227      |
| 9   | amount received by currency (local)                           | BRL=17,216,166.82, COP=20,096,349,720.00               |
| 10  | amount received in USD (rate of payment date)                 | 7,839,742.28                                           |
| 11  | legacy_v1: last payment (Bogotá date / UTC ts)                | 2025-06-30 / 2025-07-01 03:03:00                       |
| 12  | core_v2: first payment (Bogotá date / UTC ts)                 | 2025-06-30 / 2025-07-01 00:04:00                       |
| 13  | payments dated after the snapshot (2026-06-30)                | 1                                                      |
| 14  | payments before their loan was disbursed                      | 0                                                      |
| 15  | payments per valid loan: min / median / max                   | 0 / 4.0 / 18                                           |
| 16  | valid loans with no effective payment yet                     | 2240                                                   |
| 17  | valid loans paid in full or more (paid >= plan total)         | 18890                                                  |
| 18  | valid loans overpaid (paid > plan total + 1 unit)             | 0                                                      |
| 19  | legacy payment size check: median amount / median installment | 1.0                                                    |
