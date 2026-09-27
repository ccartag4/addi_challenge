# Business questions - official result queries

Generated 2026-09-27 09:15 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## q01_applications

Source: `analyses/results/q01_applications.sql` - 1 row(s)

| valid_applications | approved_applications | rejected_applications | approval_rate_pct | deleted_applications_excluded | applications_in_cdc |
|--------------------|-----------------------|-----------------------|-------------------|-------------------------------|---------------------|
| 59059              | 33007                 | 26052                 | 55.8882           | 941                           | 60000               |

## q02_loans_gmv

Source: `analyses/results/q02_loans_gmv.sql` - 3 row(s)

| currency | valid_loans | principal_local | gmv_usd    | share_of_gmv_pct |
|----------|-------------|-----------------|------------|------------------|
| BRL      | 11349       | 19214166.76     | 3514482.19 | 40.02            |
| COP      | 16606       | 22579937000.00  | 5266459.97 | 59.98            |
| TOTAL    | 27955       | 22599151166.76  | 8780942.16 | 100.0            |

## q03_cohort_2026_01

Source: `analyses/results/q03_cohort_2026_01.sql` - 3 row(s)

| source                                          | loans | gmv_usd   |
|-------------------------------------------------|-------|-----------|
| silver.fct_loan                                 | 1540  | 473272.15 |
| gold.agg_merchant_monthly                       | 1540  | 473272.15 |
| silver.fct_loan, UTC month (for reference only) | 1541  | 475211.61 |

## q04_fpd30

Source: `analyses/results/q04_fpd30.sql` - 2 row(s)

| scope          | fpd30_eligible_loans | fpd30_loans | fpd30_unpaid | fpd30_paid_late | fpd30_pct |
|----------------|----------------------|-------------|--------------|-----------------|-----------|
| global         | 24821                | 2204        | 547          | 1657            | 8.8796    |
| cohort 2026-01 | 1540                 | 120         | 38           | 82              | 7.7922    |

## q05_par30

Source: `analyses/results/q05_par30.sql` - 6 row(s)

| dpd_bucket | loans | loans_with_balance | outstanding_usd | share_of_outstanding_pct | par30_outstanding_usd | par30_pct |
|------------|-------|--------------------|-----------------|--------------------------|-----------------------|-----------|
| 0          | 25098 | 6208               | 1424487.98      | 68.84                    |                       |           |
| 1-30       | 947   | 947                | 220489.67       | 10.66                    |                       |           |
| 31-60      | 292   | 292                | 61134.74        | 2.95                     | 61134.74              | 100.0     |
| 61-90      | 125   | 125                | 25929.84        | 1.25                     | 25929.84              | 100.0     |
| 90+        | 1493  | 1493               | 337133.16       | 16.29                    | 337133.16             | 100.0     |
| TOTAL      | 27955 | 9065               | 2069175.39      | 100.0                    | 424197.74             | 20.5008   |

## q06_top_merchants

Source: `analyses/results/q06_top_merchants.sql` - 5 row(s)

| gmv_rank | merchant_id | merchant_name       | country | current_category | scd2_versions | loans | gmv_usd    | gmv_share_pct | approval_rate_pct | fpd30_pct | outstanding_usd_at_snapshot | par30_pct_at_snapshot |
|----------|-------------|---------------------|---------|------------------|---------------|-------|------------|---------------|-------------------|-----------|-----------------------------|-----------------------|
| 1        | 1607        | Comercio 1607 SA    | BR      | EDUCATION        | 1             | 6675  | 2062698.44 | 23.49         | 56.05             | 9.63      | 464989.66                   | 21.51                 |
| 2        | 1397        | Comercio 1397 Shop  | CO      | HEALTH           | 1             | 2184  | 683302.34  | 7.78          | 55.27             | 8.54      | 173968.97                   | 20.42                 |
| 3        | 1664        | Comercio 1664 SA    | CO      | HEALTH           | 2             | 1207  | 379017.69  | 4.32          | 56.55             | 8.1       | 94586.81                    | 17.21                 |
| 4        | 1030        | Comercio 1030 Shop  | CO      | FASHION          | 1             | 609   | 206931.64  | 2.36          | 54.41             | 8.24      | 48139.80                    | 16.23                 |
| 5        | 1286        | Comercio 1286 Store | CO      | TRAVEL           | 1             | 477   | 148238.13  | 1.69          | 53.99             | 10.05     | 36287.18                    | 22.87                 |

## q06b_concentration

Source: `analyses/results/q06b_concentration.sql` - 8 row(s)

| segment                            | merchants | gmv_usd | gmv_share_pct | fpd30_pct | outstanding_usd_at_snapshot | outstanding_share_pct | par30_pct_at_snapshot | merchants_for_50pct_gmv | merchants_for_80pct_gmv |
|------------------------------------|-----------|---------|---------------|-----------|-----------------------------|-----------------------|-----------------------|-------------------------|-------------------------|
| 0. portfolio                       | 700       | 8780942 | 100.0         | 8.88      | 2069175                     | 100.0                 | 20.5                  | 15                      | 141                     |
| 1. top 1 (merchant 1607)           | 1         | 2062698 | 23.49         | 9.63      | 464990                      | 22.47                 | 21.51                 | 15                      | 141                     |
| 2. rank 2-5                        | 4         | 1417490 | 16.14         | 8.54      | 352983                      | 17.06                 | 19.24                 | 15                      | 141                     |
| 3. rank 6-20                       | 15        | 1249016 | 14.22         | 8.52      | 286671                      | 13.85                 | 19.3                  | 15                      | 141                     |
| 4. rank 21-698                     | 680       | 4051738 | 46.14         | 8.72      | 964532                      | 46.61                 | 20.83                 | 15                      | 141                     |
| 5. portfolio without merchant 1607 | 699       | 6718244 | 76.51         | 8.64      | 1604186                     | 77.53                 | 20.21                 | 15                      | 141                     |
| 6. country BR                      | 196       | 3514482 | 40.02         | 9.23      | 783725                      | 37.88                 | 21.67                 | 15                      | 141                     |
| 6. country CO                      | 504       | 5266460 | 59.98         | 8.64      | 1285450                     | 62.12                 | 19.79                 | 15                      | 141                     |

## q07_customers

Source: `analyses/results/q07_customers.sql` - 1 row(s)

| customer_ids | real_people | redundant_customer_ids | people_with_2_ids | people_with_ids_in_2_countries | alt_people_document_plus_country | alt_redundant_document_plus_country |
|--------------|-------------|------------------------|-------------------|--------------------------------|----------------------------------|-------------------------------------|
| 30000        | 29093       | 907                    | 907               | 346                            | 29439                            | 561                                 |
