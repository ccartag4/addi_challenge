# Delinquency snapshot as of 2026-06-30 - PAR30 and sensitivity

Generated 2026-09-27 02:09 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_17_delinquency_snapshot

Source: `analyses/profiling/dq_17_delinquency_snapshot.sql` - 18 row(s)

| seq | metric                                                                | value                                                                                                                                                   |
|-----|-----------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | loans in snapshot (= valid loans)                                     | 27955                                                                                                                                                   |
| 2   | as_of_date / FX rates used                                            | 2026-06-30 / BRL=5.611300, COP=4141.000000                                                                                                              |
| 3   | loans by status                                                       | CURRENT=6208, DELINQUENT=2857, SETTLED=18890                                                                                                            |
| 4   | loans by DPD bucket (loans / outstanding USD / share of USD)          | 0: 25098 / 1,424,488 / 68.84% | 1-30: 947 / 220,490 / 10.66% | 31-60: 292 / 61,135 / 2.95% | 61-90: 125 / 25,930 / 1.25% | 90+: 1493 / 337,133 / 16.29% |
| 5   | total outstanding balance USD (Q5)                                    | 2,069,175.39                                                                                                                                            |
| 6   | outstanding USD of loans with DPD > 30 (PAR30 numerator)              | 424,197.74                                                                                                                                              |
| 7   | PAR30 (Q5)                                                            | 20.5008 %                                                                                                                                               |
| 8   | loans with DPD > 30 / loans with balance                              | 1910 / 9065                                                                                                                                             |
| 9   | outstanding by currency: local / USD                                  | BRL: 4,397,718.37 / 783,725.41 | COP: 5,323,048,400.00 / 1,285,449.99                                                                                   |
| 10  | PAR30 by currency                                                     | BRL=21.67%, COP=19.79%                                                                                                                                  |
| 11  | sensitivity A11: outstanding net of partial payments (USD) / PAR30    | 2,057,634.75 / 20.5683 %                                                                                                                                |
| 12  | sensitivity A12: outstanding at disbursement-date rates (USD) / PAR30 | 2,047,237.02 / 20.491 %                                                                                                                                 |
| 13  | overdue amount USD (installments already due and unpaid)              | 468,613.91                                                                                                                                              |
| 14  | delinquent loans: median / max days since last payment                | 99.0 / 509                                                                                                                                              |
| 15  | delinquent loans that never paid anything                             | 735                                                                                                                                                     |
| 16  | PAR30 by disbursement year                                            | 2025=77.88%, 2026=6.43%                                                                                                                                 |
| 17  | consistency with dq_16: FPD30 eligible / flagged from the mart        | 24821 / 2204                                                                                                                                            |
| 18  | top 5 merchants by outstanding USD (share of total)                   | 1607: 464,990 (22.47%) | 1397: 173,969 (8.41%) | 1664: 94,587 (4.57%) | 1030: 48,140 (2.33%) | 1286: 36,287 (1.75%)                                     |
