# Row-count funnel per extract and layer

Generated 2026-09-27 01:53 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_15_row_count_funnel

Source: `analyses/profiling/dq_15_row_count_funnel.sql` - 30 row(s)

| extract           | stage | model                                             | rows   | delta_vs_previous |
|-------------------|-------|---------------------------------------------------|--------|-------------------|
| applications_cdc  | 1     | bronze.brz_applications_cdc                       | 128197 |                   |
| applications_cdc  | 2     | silver.stg_applications_cdc                       | 121087 | -7110             |
| applications_cdc  | 3     | silver.int_application_events                     | 121087 | 0                 |
| applications_cdc  | 4     | silver.fct_application (all applications)         | 60000  | -61087            |
| applications_cdc  | 5     | silver.fct_application where is_valid             | 59059  | -941              |
| applications_cdc  | 6     | silver.fct_application where is_approved          | 33007  | -26052            |
| customers         | 1     | bronze.brz_customers                              | 30000  |                   |
| customers         | 2     | silver.stg_customers                              | 30000  | 0                 |
| customers         | 3     | silver.bridge_customer_person (customer_id grain) | 30000  | 0                 |
| customers         | 4     | silver.dim_customer (person grain)                | 29093  | -907              |
| fx_rates          | 1     | bronze.brz_fx_rates                               | 848    |                   |
| fx_rates          | 2     | silver.stg_fx_rates                               | 848    | 0                 |
| fx_rates          | 3     | silver.int_fx_daily (calendar days x currency)    | 1200   | 352               |
| fx_rates          | 4     | silver.int_fx_daily where is_published            | 848    | -352              |
| installments      | 1     | bronze.brz_installments                           | 130297 |                   |
| installments      | 2     | silver.stg_installments                           | 130297 | 0                 |
| installments      | 3     | silver.stg_installments on valid loans            | 130297 | 0                 |
| loans             | 1     | bronze.brz_loans                                  | 28075  |                   |
| loans             | 2     | silver.stg_loans                                  | 28075  | 0                 |
| loans             | 3     | silver.int_loan_validated                         | 28075  | 0                 |
| loans             | 4     | silver.fct_loan (valid loans)                     | 27955  | -120              |
| merchants_history | 1     | bronze.brz_merchants_history                      | 862    |                   |
| merchants_history | 2     | silver.stg_merchants_history                      | 862    | 0                 |
| merchants_history | 3     | silver.dim_merchant (versions)                    | 862    | 0                 |
| merchants_history | 4     | silver.dim_merchant where is_current (merchants)  | 700    | -162              |
| payments          | 1     | bronze.brz_payments                               | 112339 |                   |
| payments          | 2     | silver.stg_payments                               | 110136 | -2203             |
| payments          | 3     | silver.int_payment_classified                     | 110136 | 0                 |
| payments          | 4     | silver.int_payment_classified where EFFECTIVE     | 107554 | -2582             |
| payments          | 5     | silver.fct_payment (effective, valid loans)       | 107554 | 0                 |
