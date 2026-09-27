# FIFO allocation and installment status as of the snapshot

Generated 2026-09-27 02:01 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_16_fifo_and_delinquency

Source: `analyses/profiling/dq_16_fifo_and_delinquency.sql` - 24 row(s)

| seq | metric                                                       | value                                             |
|-----|--------------------------------------------------------------|---------------------------------------------------|
| 1   | allocation rows (payment x installment)                      | 114347                                            |
| 2   | payments with >= 1 allocation / with none (pure overpayment) | 107554 / 0                                        |
| 3   | payments split across 2+ installments                        | 6772                                              |
| 4   | installments funded by 2+ payments                           | 14451                                             |
| 5   | loans with unallocated excess (> 0.01)                       | 0                                                 |
| 6   | unallocated excess by currency                               | BRL=0.00, COP=0.00                                |
| 7   | installments as of snapshot: settled / partial / unpaid      | 99542 / 245 / 30510                               |
| 8   | installments: due by snapshot / not yet due                  | 104995 / 25302                                    |
| 9   | installments overdue as of snapshot                          | 6120                                              |
| 10  | settled installments: early / on time / late 1-30 / late >30 | 46386 / 7540 / 39725 / 5891                       |
| 11  | median / max days_to_settle (settled)                        | 0.0 / 70                                          |
| 12  | max days_past_due accrued (any installment)                  | 512                                               |
| 13  | installments whose payment arrived after the snapshot        | 2                                                 |
| 14  | FPD30: eligible first installments (due <= snapshot - 30)    | 24821                                             |
| 15  | FPD30: flagged (paid > 30 days late or unpaid > 30 days)     | 2204                                              |
| 16  | FPD30 global (Q4)                                            | 8.8796 %                                          |
| 17  | FPD30 2026-01 cohort: eligible / flagged / rate (Q4)         | 1540 / 120 / 7.7922 %                             |
| 18  | FPD30 flagged: unpaid vs paid late                           | 547 unpaid / 1657 paid late                       |
| 19  | loans with outstanding balance as of snapshot                | 9065                                              |
| 20  | loans fully settled as of snapshot                           | 18890                                             |
| 21  | loans by DPD bucket as of snapshot                           | 0=25098, 1-30=947, 31-60=292, 61-90=125, 90+=1493 |
| 22  | total outstanding USD at snapshot rate (Q5 preview)          | 2,069,175.39                                      |
| 23  | PAR30 = outstanding USD of DPD > 30 / total (Q5 preview)     | 20.5008 %                                         |
| 24  | snapshot FX rates used                                       | BRL=5.611300, COP=4141.000000                     |
