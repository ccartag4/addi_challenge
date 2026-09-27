# Independent cross-check — pandas from raw CSVs vs dbt gold/silver

Generated 2026-09-27 09:05 by `scripts/crosscheck_pandas.py`. Snapshot 2026-06-30. pandas 3.0.6. 24 of 24 checks match.

The pandas column is computed from the raw CSV extracts only (own parser, own CDC resolution, own FIFO loop in integer cents). The dbt column is read from the warehouse. Tolerances: 0.01 USD on sums, 0.0001 on percentages, exact on counts.

| Q  | Measure                        | pandas (raw CSVs)                                                               | dbt (warehouse)                                                                 | match |
|----|--------------------------------|---------------------------------------------------------------------------------|---------------------------------------------------------------------------------|-------|
| Q1 | valid applications             | 59059                                                                           | 59059                                                                           | ✅     |
| Q1 | approved applications          | 33007                                                                           | 33007                                                                           | ✅     |
| Q1 | approval rate %                | 55.8882                                                                         | 55.8882                                                                         | ✅     |
| Q2 | valid loans                    | 27955                                                                           | 27955                                                                           | ✅     |
| Q2 | GMV USD                        | 8,780,942.16                                                                    | 8,780,942.16                                                                    | ✅     |
| Q3 | 2026-01 loans                  | 1540                                                                            | 1540                                                                            | ✅     |
| Q3 | 2026-01 GMV USD                | 473,272.15                                                                      | 473,272.15                                                                      | ✅     |
| Q4 | FPD30 eligible (global)        | 24821                                                                           | 24821                                                                           | ✅     |
| Q4 | FPD30 flagged (global)         | 2204                                                                            | 2204                                                                            | ✅     |
| Q4 | FPD30 % (global)               | 8.8796                                                                          | 8.8796                                                                          | ✅     |
| Q4 | FPD30 eligible (2026-01)       | 1540                                                                            | 1540                                                                            | ✅     |
| Q4 | FPD30 flagged (2026-01)        | 120                                                                             | 120                                                                             | ✅     |
| Q4 | FPD30 % (2026-01)              | 7.7922                                                                          | 7.7922                                                                          | ✅     |
| Q5 | outstanding USD                | 2,069,175.39                                                                    | 2,069,175.39                                                                    | ✅     |
| Q5 | PAR30 numerator USD            | 424,197.74                                                                      | 424,197.74                                                                      | ✅     |
| Q5 | PAR30 %                        | 20.5008                                                                         | 20.5008                                                                         | ✅     |
| Q6 | top 5 merchants (id: GMV USD)  | 1607: 2,062,698 | 1397: 683,302 | 1664: 379,018 | 1030: 206,932 | 1286: 148,238 | 1607: 2,062,698 | 1397: 683,302 | 1664: 379,018 | 1030: 206,932 | 1286: 148,238 | ✅     |
| Q7 | customer_ids                   | 30000                                                                           | 30000                                                                           | ✅     |
| Q7 | real people                    | 29093                                                                           | 29093                                                                           | ✅     |
| Q7 | redundant ids                  | 907                                                                             | 907                                                                             | ✅     |
| —  | effective payments             | 107554                                                                          | 107554                                                                          | ✅     |
| —  | loans present on one side only | 0                                                                               | 0                                                                               | ✅     |
| —  | loans with a different DPD     | 0                                                                               | 0                                                                               | ✅     |
| —  | loans with a different balance | 0                                                                               | 0                                                                               | ✅     |

## Notes

- Applications resolved: 60,000 (deleted 941); valid loans: 27,955; installments: 130,297; effective payments on or before the snapshot: 107,553.
- Alternative Q7 identity (document + country): 29,439 people, 561 redundant ids.
- Loan-by-loan: 27,955 loans compared on DPD and outstanding balance.
