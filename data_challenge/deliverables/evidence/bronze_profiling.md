# Bronze profiling — raw extract data quality

Generated 2026-09-27 00:27 by `scripts/run_analyses.py` from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `lumo.duckdb` (read-only).

## dq_01_timestamp_formats

Source: `analyses/profiling/dq_01_timestamp_formats.sql` — 17 row(s)

| col                               | shape                | n_rows | example              |
|-----------------------------------|----------------------|--------|----------------------|
| applications_cdc._ingested_at_utc | 9999-99-99 99:99:99  | 128197 | 2025-01-01 00:09:48  |
| applications_cdc.event_at_utc     | 9999-99-99 99:99:99  | 106268 | 2025-01-01 00:16:57  |
| applications_cdc.event_at_utc     | 9999-99-99T99:99:99Z | 15530  | 2025-01-01T00:00:34Z |
| applications_cdc.event_at_utc     | 9999999999999        | 6399   | 1735693313000        |
| customers._ingested_at            | 9999-99-99 99:99:99  | 30000  | 2022-07-17 04:00:00  |
| customers.created_at              | 9999-99-99 99:99:99  | 24770  | 2022-07-17 00:00:00  |
| customers.created_at              | 9999-99-99T99:99:99Z | 3713   | 2022-07-17T00:00:00Z |
| customers.created_at              | 9999999999999        | 1517   | 1658016000000        |
| fx_rates.rate_date                | 9999-99-99           | 848    | 2024-12-23           |
| installments.due_date             | 9999-99-99           | 130297 | 2025-02-02           |
| loans.disbursed_at_utc            | 9999-99-99 99:99:99  | 23278  | 2025-01-02 11:08:45  |
| loans.disbursed_at_utc            | 9999-99-99T99:99:99Z | 3357   | 2025-01-03T00:44:57Z |
| loans.disbursed_at_utc            | 9999999999999        | 1440   | 1735886703000        |
| merchants_history.valid_from      | 9999-99-99           | 862    | 2023-02-03           |
| payments.paid_at_utc              | 9999-99-99 99:99:99  | 93040  | 2025-01-27 22:37:00  |
| payments.paid_at_utc              | 9999-99-99T99:99:99Z | 13574  | 2025-01-31T06:24:00Z |
| payments.paid_at_utc              | 9999999999999        | 5725   | 1738129860000        |

## dq_02_duplicates

Source: `analyses/profiling/dq_02_duplicates.sql` — 7 row(s)

| extract           | declared_key                        | total_rows | distinct_rows | exact_duplicate_rows | key_duplicate_rows |
|-------------------|-------------------------------------|------------|---------------|----------------------|--------------------|
| applications_cdc  | application_id + event_at_utc + _op | 128197     | 123213        | 4984                 | 104                |
| customers         | customer_id                         | 30000      | 30000         | 0                    | 0                  |
| fx_rates          | rate_date + currency                | 848        | 848           | 0                    | 0                  |
| installments      | loan_id + installment_number        | 130297     | 130297        | 0                    | 0                  |
| loans             | loan_id                             | 28075      | 28075         | 0                    | 0                  |
| merchants_history | merchant_id + valid_from            | 862        | 862           | 0                    | 0                  |
| payments          | payment_id                          | 112339     | 110802        | 1537                 | 666                |

## dq_03_cdc_applications

Source: `analyses/profiling/dq_03_cdc_applications.sql` — 19 row(s)

| seq | metric                                           | value    |
|-----|--------------------------------------------------|----------|
| 1   | rows after exact dedup                           | 123213   |
| 2   | distinct application_id                          | 60000    |
| 3   | rows with _op = I                                | 61129    |
| 4   | rows with _op = U                                | 61131    |
| 5   | rows with _op = D                                | 953      |
| 6   | other _op values                                 | 0        |
| 7   | applications with at least one D event           | 941      |
| 8   | rows with status CREATED                         | 61129    |
| 9   | rows with status APPROVED                        | 34712    |
| 10  | rows with status REJECTED                        | 27372    |
| 11  | rows with other / null status                    | 0        |
| 12  | currency values                                  | BRL, COP |
| 13  | (application_id, event_at_utc) pairs with >1 row | 104      |
| 14  | APPROVED rows with null approved_amount          | 0        |
| 15  | rows with approved_amount > requested_amount     | 0        |
| 16  | rows with requested_amount <= 0 or null          | 0        |
| 17  | applications with >1 distinct customer_id        | 1345     |
| 18  | applications with >1 distinct merchant_id        | 0        |
| 19  | rows with null customer_id or merchant_id        | 0        |

## dq_04_loans_integrity

Source: `analyses/profiling/dq_04_loans_integrity.sql` — 18 row(s)

| seq | metric                                                            | value                    |
|-----|-------------------------------------------------------------------|--------------------------|
| 1   | loan rows                                                         | 28075                    |
| 2   | distinct loan_id                                                  | 28075                    |
| 3   | status values                                                     | DISBURSED                |
| 4   | currency values                                                   | BRL, COP                 |
| 5   | term_months values                                                | 12, 3, 4, 6              |
| 6   | loans whose application_id is not in the CDC at all               | 120                      |
| 7   | loans whose application has a D event                             | 0                        |
| 8   | loans whose customer_id never appears on their application        | 0                        |
| 9   | loans whose merchant_id never appears on their application        | 0                        |
| 10  | loans whose currency never appears on their application           | 0                        |
| 11  | loans whose principal <> any approved_amount of their application | 0                        |
| 12  | loans with principal <= 0 or null                                 | 0                        |
| 13  | applications with >1 loan                                         | 0                        |
| 14  | loans without installments                                        | 120                      |
| 15  | loans where #installments <> term_months                          | 0                        |
| 16  | installment rows whose loan_id is not in loans                    | 0                        |
| 17  | installments with amount_due <= 0 or null                         | 0                        |
| 18  | installment due_date range                                        | 2025-02-02 .. 2027-06-30 |

## dq_05_payments

Source: `analyses/profiling/dq_05_payments.sql` — 21 row(s)

| seq | metric                                                | value                                                                                         |
|-----|-------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| 1   | rows                                                  | 112339                                                                                        |
| 2   | rows after exact dedup                                | 110802                                                                                        |
| 3   | distinct payment_id                                   | 110136                                                                                        |
| 4   | payment_id with >1 distinct row after dedup           | 666                                                                                           |
| 5   | columns that differ within those payment_ids          | paid_at_utc                                                                                   |
| 6   | source_system x status                                | core_v2/REVERSED=1063, core_v2/SETTLED=88717, legacy_v1/REVERSED=233, legacy_v1/SETTLED=20789 |
| 7   | loan_ref shapes by source                             | core_v2: 999999 x89780 | legacy_v1: LN-999999 x21022                                          |
| 8   | payment_method values                                 | PSE, CARD, TRANSFER, CASH                                                                     |
| 9   | REVERSED rows with null reversed_payment_id           | 0                                                                                             |
| 10  | REVERSED rows whose target payment_id does not exist  | 0                                                                                             |
| 11  | REVERSED rows whose target is itself REVERSED         | 0                                                                                             |
| 12  | target payments reversed by >1 reversal row           | 5                                                                                             |
| 13  | REVERSED rows with negative amount                    | 1296                                                                                          |
| 14  | REVERSED rows where |amount| <> target amount         | 0                                                                                             |
| 15  | REVERSED rows in a different source than their target | 0                                                                                             |
| 16  | SETTLED rows with amount <= 0 or null                 | 0                                                                                             |
| 17  | payments whose normalized loan ref is not in loans    | 0                                                                                             |
| 18  | median amount / median installment — legacy_v1 COP    | 100.0                                                                                         |
| 19  | median amount / median installment — legacy_v1 BRL    | 100.0                                                                                         |
| 20  | median amount / median installment — core_v2 COP      | 1.0                                                                                           |
| 21  | median amount / median installment — core_v2 BRL      | 1.0                                                                                           |

## dq_06_fx_gaps

Source: `analyses/profiling/dq_06_fx_gaps.sql` — 2 row(s)

| currency | published_days | first_date | last_date  | missing_days | missing_weekend_days | missing_weekday_days | missing_weekday_dates                                                  | min_rate | max_rate | invalid_rates |
|----------|----------------|------------|------------|--------------|----------------------|----------------------|------------------------------------------------------------------------|----------|----------|---------------|
| BRL      | 424            | 2024-12-23 | 2026-08-14 | 176          | 170                  | 6                    | 2025-01-01, 2025-04-18, 2025-12-25, 2026-01-01, 2026-04-03, 2026-05-01 | 5.0692   | 5.7997   | 0             |
| COP      | 424            | 2024-12-23 | 2026-08-14 | 176          | 170                  | 6                    | 2025-01-01, 2025-04-18, 2025-12-25, 2026-01-01, 2026-04-03, 2026-05-01 | 4043.74  | 4525.79  | 0             |

## dq_07_customers

Source: `analyses/profiling/dq_07_customers.sql` — 20 row(s)

| seq | metric                                                     | value                                             |
|-----|------------------------------------------------------------|---------------------------------------------------|
| 1   | rows                                                       | 30000                                             |
| 2   | distinct customer_id                                       | 30000                                             |
| 3   | distinct document_number                                   | 29093                                             |
| 4   | redundant customer_ids (rows - distinct documents)         | 907                                               |
| 5   | documents held by >1 customer_id                           | 907                                               |
| 6   |   of which spanning >1 country                             | 346                                               |
| 7   |   of which with >1 birth_year                              | 886                                               |
| 8   |   of which sharing one normalized email                    | 4                                                 |
| 9   | document_number shapes                                     | 99999999 x30000                                   |
| 10  | country values                                             | BR=8391, CO=21609                                 |
| 11  | monthly_income non-numeric shapes (top 6)                  | 9,999,999 x2678, N/A x1505, -9 x858, 999,999 x828 |
| 12  | monthly_income = -1                                        | 858                                               |
| 13  | monthly_income null                                        | 0                                                 |
| 14  | birth_year min .. max                                      | 1900 .. 2005                                      |
| 15  | birth_year = 1900 (placeholder?)                           | 63                                                |
| 16  | distinct city raw                                          | 14                                                |
| 17  | distinct city normalized (lower, trim, no accents)         | 11                                                |
| 18  | emails not already lower(trim(email))                      | 30000                                             |
| 19  | customer_ids referenced by the CDC but missing from master | 1                                                 |
| 20  | CDC rows pointing to those missing customer_ids            | 1353                                              |

## dq_08_merchants

Source: `analyses/profiling/dq_08_merchants.sql` — 14 row(s)

| seq | metric                                             | value                                                                                          |
|-----|----------------------------------------------------|------------------------------------------------------------------------------------------------|
| 1   | rows                                               | 862                                                                                            |
| 2   | distinct merchant_id                               | 700                                                                                            |
| 3   | merchants with 1 version                           | 538                                                                                            |
| 4   | merchants with 2 versions                          | 162                                                                                            |
| 5   | merchants with 3+ versions                         | 0                                                                                              |
| 6   | merchants whose category changed                   | 157                                                                                            |
| 7   | merchants whose country changed                    | 0                                                                                              |
| 8   | merchants whose name differs only by case/spaces   | 72                                                                                             |
| 9   | merchants whose normalized name really changed     | 0                                                                                              |
| 10  | category values                                    | EDUCATION=116, ELECTRONICS=121, FASHION=125, HEALTH=126, HOME=129, MOTORCYCLES=117, TRAVEL=112 |
| 11  | valid_from min .. max                              | 2023-02-03 .. 2026-04-21                                                                       |
| 12  | merchants in CDC missing from history              | 0                                                                                              |
| 13  | merchants in loans missing from history            | 0                                                                                              |
| 14  | merchants in history never used by any application | 0                                                                                              |
