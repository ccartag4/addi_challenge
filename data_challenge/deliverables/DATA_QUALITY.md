# Data Quality — DAMA-DMBOK matrix

Generated 2026-09-27 08:57 by `scripts/build_data_quality_matrix.py` from `target/manifest.json` and `target/run_results.json` (run of 2026-09-27T13:57:19Z). 244 tests over 30 models and seeds.

Every dbt test in this project declares the DMBOK dimension it protects (`config.meta.dq_dimension`). Findings and assumptions behind each test are in `ASSUMPTIONS.md`; the step that introduced it is in `WORKLOG.md` and `DATA_JOURNEY.md`.

## 1. Dimensions

| Dimension | Meaning in this project | Tests | Pass | Warn | Fail |
|---|---|---:|---:|---:|---:|
| **completeness** | required values are present (not_null, coverage of a calendar or a population) | 70 | 70 | 0 | 0 |
| **uniqueness** | one record per real-world entity at the declared grain | 27 | 27 | 0 | 0 |
| **validity** | values conform to type, format, domain and range | 64 | 64 | 0 | 0 |
| **accuracy** | values reflect the real fact (scale, conversion, conservation of money) | 14 | 14 | 0 | 0 |
| **consistency** | the same fact agrees across models and across definitions | 35 | 35 | 0 | 0 |
| **integrity** | relationships resolve (referential integrity, point-in-time coverage) | 24 | 23 | 1 | 0 |
| **timeliness** | ordering and dating are correct (event vs ingest time, cutovers, as-of dates) | 10 | 10 | 0 | 0 |
| **total** | | 244 | 243 | 1 | 0 |

## 2. Matrix: model × dimension (number of tests; ⚠️ = warns, ❌ = fails)

| Layer | Model | completeness | uniqueness | validity | accuracy | consistency | integrity | timeliness | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bronze | `brz_applications_cdc` | 1 |  |  |  |  |  |  | 1 |
| bronze | `brz_customers` | 1 |  |  |  |  |  |  | 1 |
| bronze | `brz_fx_rates` | 2 |  |  |  |  |  |  | 2 |
| bronze | `brz_installments` | 2 |  |  |  |  |  |  | 2 |
| bronze | `brz_loans` | 1 |  |  |  |  |  |  | 1 |
| bronze | `brz_merchants_history` | 2 |  |  |  |  |  |  | 2 |
| bronze | `brz_payments` | 1 |  |  |  |  |  |  | 1 |
| silver/staging | `stg_applications_cdc` | 2 |  | 6 | 1 |  |  |  | 9 |
| silver/staging | `stg_customers` | 2 | 1 | 3 |  | 1 | 1 |  | 8 |
| silver/staging | `stg_fx_rates` |  | 1 | 2 |  |  |  |  | 3 |
| silver/staging | `stg_installments` | 1 | 1 | 1 | 1 |  |  |  | 4 |
| silver/staging | `stg_loans` | 2 | 1 | 6 |  |  | 1 |  | 10 |
| silver/staging | `stg_merchants_history` | 1 | 1 | 2 |  |  |  |  | 4 |
| silver/staging | `stg_payments` | 2 | 1 | 5 | 2 | 1 |  | 1 | 12 |
| silver/intermediate | `int_application_events` |  |  | 1 |  |  |  |  | 1 |
| silver/intermediate | `int_fx_daily` | 3 | 1 | 2 |  | 1 |  | 2 | 9 |
| silver/intermediate | `int_loan_month_end_status` | 2 | 1 | 2 |  | 2 | 1 | 1 | 9 |
| silver/intermediate | `int_loan_validated` | 1 | 1 | 1 |  | 2 |  |  | 5 |
| silver/intermediate | `int_payment_allocation` | 1 | 1 | 1 | 3 | 1 | 1 |  | 8 |
| silver/intermediate | `int_payment_classified` | 2 | 1 | 1 | 1 | 2 | 1 |  | 8 |
| silver/core | `bridge_customer_person` | 2 | 1 |  |  | 1 | 3 |  | 7 |
| silver/core | `dim_customer` | 2 | 3 | 2 |  | 2 | 2 | 1 | 12 |
| silver/core | `dim_merchant` | 5 | 2 | 4 |  | 4 | 1 |  | 16 |
| silver/core | `fct_application` | 4 | 1 | 4 | 1 | 1 | 5⚠️ | 1 | 17 |
| silver/core | `fct_installment_status` | 6 | 2 | 6 | 2 | 7 | 1 | 1 | 25 |
| silver/core | `fct_loan` | 8 | 2 | 2 | 2 | 3 | 5 | 3 | 25 |
| silver/core | `fct_payment` | 5 | 2 | 3 | 2 | 3 | 1 |  | 16 |
| gold | `agg_merchant_monthly` | 2 | 1 | 5 |  | 6 | 3 |  | 17 |
| gold | `dm_loan_delinquency_snapshot` | 6 | 1 | 5 | 3 | 8 | 1 |  | 24 |
| seed | `city_canonical` | 2 | 1 |  |  |  |  |  | 3 |

## 3. Business tests (singular)

| Test | Dimension | Models | Status |
|---|---|---|---|
| `assert_agg_merchant_monthly_reconciles` | consistency | `agg_merchant_monthly`, `fct_application`, `fct_loan`, `dm_loan_delinquency_snapshot` | ✅ pass |
| `assert_allocation_never_exceeds_installment` | accuracy | `int_payment_allocation`, `stg_installments` | ✅ pass |
| `assert_allocation_never_exceeds_payment` | accuracy | `int_payment_allocation`, `fct_payment` | ✅ pass |
| `assert_bridge_covers_every_customer_id` | integrity | `stg_customers`, `bridge_customer_person` | ✅ pass |
| `assert_deleted_applications_have_no_loans` | integrity | `stg_loans`, `fct_application` | ✅ pass |
| `assert_dim_merchant_no_overlapping_versions` | consistency | `dim_merchant` | ✅ pass |
| `assert_dim_merchant_one_current_version` | consistency | `dim_merchant` | ✅ pass |
| `assert_every_application_matches_one_merchant_version` | integrity | `fct_application`, `dim_merchant` | ✅ pass |
| `assert_fifo_no_skipped_installments` | consistency | `fct_installment_status` | ✅ pass |
| `assert_fx_daily_calendar_is_complete` | completeness | `int_fx_daily` | ✅ pass |
| `assert_installment_paid_reconciles_with_payments` | consistency | `fct_payment`, `fct_installment_status`, `fct_loan` | ✅ pass |
| `assert_loan_agrees_with_application` | consistency | `int_loan_validated` | ✅ pass |
| `assert_month_end_series_matches_snapshot` | consistency | `int_loan_month_end_status`, `dm_loan_delinquency_snapshot` | ✅ pass |
| `assert_no_reversed_payment_in_fct_payment` | accuracy | `fct_payment`, `stg_payments` | ✅ pass |
| `assert_payment_counts_reconcile` | consistency | `stg_payments`, `int_payment_classified`, `fct_payment` | ✅ pass |
| `assert_payment_sources_respect_cutover` | timeliness | `stg_payments` | ✅ pass |
| `assert_person_counts_reconcile` | consistency | `stg_customers`, `dim_customer`, `bridge_customer_person` | ✅ pass |
| `assert_snapshot_covers_every_valid_loan` | completeness | `fct_loan`, `dm_loan_delinquency_snapshot` | ✅ pass |
| `assert_snapshot_dpd_matches_installments` | accuracy | `fct_installment_status`, `dm_loan_delinquency_snapshot` | ✅ pass |

## 4. Tests not passing in the last run

| Test | Dimension | Severity | Status | Failing rows | Models |
|---|---|---|---|---:|---|
| `dbt_utils_expression_is_true_fct_application_not_is_valid_or_customer_id_is_not_null` | integrity | warn | warn | 3 | `fct_application` |

## 5. Coverage

Models and seeds with at least one test: 30 of 30.
Tests without a DMBOK dimension: 0.

## 6. All tests

| Layer | Model(s) | Test | Kind | Dimension | Severity | Status |
|---|---|---|---|---|---|---|
| bronze | `brz_applications_cdc` | `not_null_brz_applications_cdc_application_id` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_customers` | `not_null_brz_customers_customer_id` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_fx_rates` | `not_null_brz_fx_rates_currency` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_fx_rates` | `not_null_brz_fx_rates_rate_date` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_installments` | `not_null_brz_installments_installment_number` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_installments` | `not_null_brz_installments_loan_id` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_loans` | `not_null_brz_loans_loan_id` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_merchants_history` | `not_null_brz_merchants_history_merchant_id` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_merchants_history` | `not_null_brz_merchants_history_valid_from` | generic: not_null | completeness | error | ✅ pass |
| bronze | `brz_payments` | `not_null_brz_payments_payment_id` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `accepted_values_stg_applications_cdc_cdc_op__I__U__D` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `accepted_values_stg_applications_cdc_currency__COP__BRL` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `accepted_values_stg_applications_cdc_status__CREATED__APPROVED__REJECTED` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `dbt_utils_accepted_range_stg_applications_cdc_requested_amount__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `dbt_utils_expression_is_true_stg_applications_cdc_approved_amount_is_null_or_approved_amount_requested_amount` | generic: expression_is_true | accuracy | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `dbt_utils_expression_is_true_stg_applications_cdc_status_APPROVED_or_approved_amount_is_not_null` | generic: expression_is_true | completeness | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `not_null_stg_applications_cdc_application_id` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `not_null_stg_applications_cdc_event_at_utc` | generic: not_null | validity | error | ✅ pass |
| silver/staging | `stg_applications_cdc` | `not_null_stg_applications_cdc_ingested_at_utc` | generic: not_null | validity | error | ✅ pass |
| silver/staging | `stg_customers` | `accepted_values_stg_customers_country__CO__BR` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_customers`, `bridge_customer_person` | `assert_bridge_covers_every_customer_id` | singular | integrity | error | ✅ pass |
| silver/staging | `stg_customers`, `dim_customer`, `bridge_customer_person` | `assert_person_counts_reconcile` | singular | consistency | error | ✅ pass |
| silver/staging | `stg_customers` | `dbt_utils_accepted_range_stg_customers_birth_year__2010__1901` | generic: accepted_range | validity | error | ✅ pass |
| silver/staging | `stg_customers` | `dbt_utils_accepted_range_stg_customers_monthly_income__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/staging | `stg_customers` | `not_null_stg_customers_customer_id` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_customers` | `not_null_stg_customers_document_number` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_customers` | `unique_stg_customers_customer_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/staging | `stg_fx_rates` | `accepted_values_stg_fx_rates_currency__COP__BRL` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_fx_rates` | `dbt_utils_accepted_range_stg_fx_rates_units_per_usd__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/staging | `stg_fx_rates` | `dbt_utils_unique_combination_of_columns_stg_fx_rates_rate_date__currency` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/staging | `stg_installments` | `dbt_utils_accepted_range_stg_installments_amount_due__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/staging | `stg_installments` | `dbt_utils_unique_combination_of_columns_stg_installments_loan_id__installment_number` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/staging | `stg_installments` | `not_null_stg_installments_due_date` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_loans` | `accepted_values_stg_loans_currency__COP__BRL` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_loans` | `accepted_values_stg_loans_status__DISBURSED` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_loans` | `accepted_values_stg_loans_term_months__False__3__4__6__12` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_loans`, `fct_application` | `assert_deleted_applications_have_no_loans` | singular | integrity | error | ✅ pass |
| silver/staging | `stg_loans` | `dbt_utils_accepted_range_stg_loans_apr__1__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/staging | `stg_loans` | `dbt_utils_accepted_range_stg_loans_principal__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/staging | `stg_loans` | `not_null_stg_loans_application_id` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_loans` | `not_null_stg_loans_disbursed_at_utc` | generic: not_null | validity | error | ✅ pass |
| silver/staging | `stg_loans` | `not_null_stg_loans_loan_id` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_loans` | `unique_stg_loans_loan_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/staging | `stg_merchants_history` | `accepted_values_stg_merchants_history_category__HOME__HEALTH__FASHION__ELECTRONICS__MOTORCYCLES__EDUCATION__TRAVEL` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_merchants_history` | `accepted_values_stg_merchants_history_country__CO__BR` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_merchants_history` | `dbt_utils_unique_combination_of_columns_stg_merchants_history_merchant_id__valid_from` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/staging | `stg_merchants_history` | `not_null_stg_merchants_history_valid_from` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_payments` | `accepted_values_stg_payments_payment_method__PSE__CARD__CASH__TRANSFER` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_payments` | `accepted_values_stg_payments_source_system__legacy_v1__core_v2` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_payments` | `accepted_values_stg_payments_status__SETTLED__REVERSED` | generic: accepted_values | validity | error | ✅ pass |
| silver/staging | `stg_payments`, `int_payment_classified`, `fct_payment` | `assert_payment_counts_reconcile` | singular | consistency | error | ✅ pass |
| silver/staging | `stg_payments` | `assert_payment_sources_respect_cutover` | singular | timeliness | error | ✅ pass |
| silver/staging | `stg_payments` | `dbt_utils_expression_is_true_stg_payments__status_SETTLED_and_amount_0_or_status_REVERSED_and_amount_0_` | generic: expression_is_true | accuracy | error | ✅ pass |
| silver/staging | `stg_payments` | `dbt_utils_expression_is_true_stg_payments_status_REVERSED_or_reversed_payment_id_is_not_null` | generic: expression_is_true | completeness | error | ✅ pass |
| silver/staging | `stg_payments` | `not_null_stg_payments_loan_id` | generic: not_null | validity | error | ✅ pass |
| silver/staging | `stg_payments` | `not_null_stg_payments_paid_at_utc` | generic: not_null | validity | error | ✅ pass |
| silver/staging | `stg_payments` | `not_null_stg_payments_payment_id` | generic: not_null | completeness | error | ✅ pass |
| silver/staging | `stg_payments` | `unique_stg_payments_payment_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/intermediate | `int_application_events` | `dbt_utils_expression_is_true_int_application_events_rn_event_desc_1_and_rn_ingest_desc_1_and_rn_event_asc_1` | generic: expression_is_true | validity | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `accepted_values_int_fx_daily_currency__COP__BRL` | generic: accepted_values | validity | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `assert_fx_daily_calendar_is_complete` | singular | completeness | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `dbt_utils_accepted_range_int_fx_daily_days_stale__5__0` | generic: accepted_range | timeliness | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `dbt_utils_accepted_range_int_fx_daily_units_per_usd__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `dbt_utils_expression_is_true_int_fx_daily_not_is_published_or_days_stale_0` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `dbt_utils_expression_is_true_int_fx_daily_rate_source_date_rate_date` | generic: expression_is_true | timeliness | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `dbt_utils_unique_combination_of_columns_int_fx_daily_rate_date__currency` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `not_null_int_fx_daily_rate_source_date` | generic: not_null | completeness | error | ✅ pass |
| silver/intermediate | `int_fx_daily` | `not_null_int_fx_daily_units_per_usd` | generic: not_null | completeness | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status`, `dm_loan_delinquency_snapshot` | `assert_month_end_series_matches_snapshot` | singular | consistency | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status` | `dbt_utils_accepted_range_int_loan_month_end_status_dpd__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status` | `dbt_utils_accepted_range_int_loan_month_end_status_outstanding_local__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status` | `dbt_utils_expression_is_true_int_loan_month_end_status__dpd_0_n_overdue_0_and_is_par30_dpd_30_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status` | `dbt_utils_expression_is_true_int_loan_month_end_status_month_end_disbursed_date` | generic: expression_is_true | timeliness | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status` | `dbt_utils_unique_combination_of_columns_int_loan_month_end_status_loan_id__month_end` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status` | `not_null_int_loan_month_end_status_loan_id` | generic: not_null | completeness | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status` | `not_null_int_loan_month_end_status_outstanding_usd` | generic: not_null | completeness | error | ✅ pass |
| silver/intermediate | `int_loan_month_end_status` | `relationships_int_loan_month_end_status_loan_id__loan_id__ref_fct_loan_` | generic: relationships | integrity | error | ✅ pass |
| silver/intermediate | `int_loan_validated` | `accepted_values_int_loan_validated_exclusion_reason__NO_APPLICATION__APPLICATION_DELETED__APPLICATION_NOT_APPROVED` | generic: accepted_values | validity | error | ✅ pass |
| silver/intermediate | `int_loan_validated` | `assert_loan_agrees_with_application` | singular | consistency | error | ✅ pass |
| silver/intermediate | `int_loan_validated` | `dbt_utils_expression_is_true_int_loan_validated_is_valid_exclusion_reason_is_null_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/intermediate | `int_loan_validated` | `not_null_int_loan_validated_loan_id` | generic: not_null | completeness | error | ✅ pass |
| silver/intermediate | `int_loan_validated` | `unique_int_loan_validated_loan_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/intermediate | `int_payment_allocation`, `stg_installments` | `assert_allocation_never_exceeds_installment` | singular | accuracy | error | ✅ pass |
| silver/intermediate | `int_payment_allocation`, `fct_payment` | `assert_allocation_never_exceeds_payment` | singular | accuracy | error | ✅ pass |
| silver/intermediate | `int_payment_allocation` | `dbt_utils_accepted_range_int_payment_allocation_allocated_amount__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/intermediate | `int_payment_allocation` | `dbt_utils_expression_is_true_int_payment_allocation_allocated_amount_payment_amount_and_allocated_amount_amount_due` | generic: expression_is_true | accuracy | error | ✅ pass |
| silver/intermediate | `int_payment_allocation` | `dbt_utils_expression_is_true_int_payment_allocation_cum_paid_start_cum_due_end_and_cum_paid_end_cum_due_start` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/intermediate | `int_payment_allocation` | `dbt_utils_unique_combination_of_columns_int_payment_allocation_payment_id__installment_number` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/intermediate | `int_payment_allocation` | `not_null_int_payment_allocation_allocated_amount` | generic: not_null | completeness | error | ✅ pass |
| silver/intermediate | `int_payment_allocation` | `relationships_int_payment_allocation_payment_id__payment_id__ref_fct_payment_` | generic: relationships | integrity | error | ✅ pass |
| silver/intermediate | `int_payment_classified` | `accepted_values_int_payment_classified_payment_class__EFFECTIVE__REVERSED_OUT__REVERSAL_ROW` | generic: accepted_values | validity | error | ✅ pass |
| silver/intermediate | `int_payment_classified` | `dbt_utils_expression_is_true_int_payment_classified__payment_class_REVERSED_OUT_n_reversal_rows_1_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/intermediate | `int_payment_classified` | `dbt_utils_expression_is_true_int_payment_classified_not_loan_missing` | generic: expression_is_true | integrity | error | ✅ pass |
| silver/intermediate | `int_payment_classified` | `dbt_utils_expression_is_true_int_payment_classified_payment_class_REVERSED_OUT_or_abs_reversal_amount_total_amount` | generic: expression_is_true | accuracy | error | ✅ pass |
| silver/intermediate | `int_payment_classified` | `not_null_int_payment_classified_payment_class` | generic: not_null | completeness | error | ✅ pass |
| silver/intermediate | `int_payment_classified` | `not_null_int_payment_classified_payment_id` | generic: not_null | completeness | error | ✅ pass |
| silver/intermediate | `int_payment_classified` | `unique_int_payment_classified_payment_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `bridge_customer_person` | `not_null_bridge_customer_person_customer_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `bridge_customer_person` | `not_null_bridge_customer_person_person_sk` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `bridge_customer_person` | `relationships_bridge_customer_person_customer_id__customer_id__ref_stg_customers_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `bridge_customer_person` | `relationships_bridge_customer_person_person_sk__person_sk__ref_dim_customer_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `bridge_customer_person` | `unique_bridge_customer_person_customer_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `dim_customer` | `accepted_values_dim_customer_country__CO__BR` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `dim_customer` | `dbt_utils_accepted_range_dim_customer_n_customer_ids__1` | generic: accepted_range | validity | error | ✅ pass |
| silver/core | `dim_customer` | `dbt_utils_expression_is_true_dim_customer_first_created_date_last_created_date` | generic: expression_is_true | timeliness | error | ✅ pass |
| silver/core | `dim_customer` | `dbt_utils_expression_is_true_dim_customer_has_duplicate_ids_n_customer_ids_1_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `dim_customer` | `not_null_dim_customer_document_number` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `dim_customer` | `not_null_dim_customer_person_sk` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `dim_customer` | `relationships_dim_customer_city_key__city_key__ref_city_canonical_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `dim_customer` | `relationships_dim_customer_latest_customer_id__customer_id__ref_stg_customers_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `dim_customer` | `unique_dim_customer_document_number` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `dim_customer` | `unique_dim_customer_latest_customer_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `dim_customer` | `unique_dim_customer_person_sk` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `dim_merchant` | `accepted_values_dim_merchant_category__HOME__HEALTH__FASHION__ELECTRONICS__MOTORCYCLES__EDUCATION__TRAVEL__UNKNOWN` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `dim_merchant` | `accepted_values_dim_merchant_category_imputation__CARRIED_FORWARD__UNKNOWN` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `dim_merchant` | `accepted_values_dim_merchant_country__CO__BR` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `dim_merchant` | `assert_dim_merchant_no_overlapping_versions` | singular | consistency | error | ✅ pass |
| silver/core | `dim_merchant` | `assert_dim_merchant_one_current_version` | singular | consistency | error | ✅ pass |
| silver/core | `dim_merchant` | `dbt_utils_expression_is_true_dim_merchant__category_source_is_null_category_imputation_is_not_null_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `dim_merchant` | `dbt_utils_expression_is_true_dim_merchant_is_current_version_number_n_versions_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `dim_merchant` | `dbt_utils_expression_is_true_dim_merchant_valid_to_is_null_or_valid_to_valid_from` | generic: expression_is_true | validity | error | ✅ pass |
| silver/core | `dim_merchant` | `dbt_utils_unique_combination_of_columns_dim_merchant_merchant_id__valid_from` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/core | `dim_merchant` | `not_null_dim_merchant_category` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `dim_merchant` | `not_null_dim_merchant_is_current` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `dim_merchant` | `not_null_dim_merchant_merchant_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `dim_merchant` | `not_null_dim_merchant_merchant_sk` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `dim_merchant` | `not_null_dim_merchant_valid_from` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `dim_merchant` | `unique_dim_merchant_merchant_sk` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `fct_application` | `accepted_values_fct_application_currency__COP__BRL` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `fct_application` | `accepted_values_fct_application_final_status__CREATED__APPROVED__REJECTED` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `fct_application`, `dim_merchant` | `assert_every_application_matches_one_merchant_version` | singular | integrity | error | ✅ pass |
| silver/core | `fct_application` | `dbt_utils_accepted_range_fct_application_n_events__1` | generic: accepted_range | validity | error | ✅ pass |
| silver/core | `fct_application` | `dbt_utils_expression_is_true_fct_application_decided_at_utc_is_null_or_decided_at_utc_created_at_utc` | generic: expression_is_true | timeliness | error | ✅ pass |
| silver/core | `fct_application` | `dbt_utils_expression_is_true_fct_application_not_is_approved_or_approved_amount_is_not_null_and_approved_amount_requested_amount_` | generic: expression_is_true | accuracy | error | ✅ pass |
| silver/core | `fct_application` | `dbt_utils_expression_is_true_fct_application_not_is_deleted_and_is_valid_` | generic: expression_is_true | validity | error | ✅ pass |
| silver/core | `fct_application` | `dbt_utils_expression_is_true_fct_application_not_is_valid_or_customer_id_is_not_null` | generic: expression_is_true | integrity | warn | ⚠️ warn |
| silver/core | `fct_application` | `dbt_utils_expression_is_true_fct_application_not_is_valid_or_final_status_in_APPROVED_REJECTED_` | generic: expression_is_true | completeness | error | ✅ pass |
| silver/core | `fct_application` | `not_null_fct_application_application_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_application` | `not_null_fct_application_created_date` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_application` | `not_null_fct_application_merchant_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_application` | `relationships_fct_application_customer_id__customer_id__ref_stg_customers_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `fct_application` | `relationships_fct_application_merchant_id__merchant_id__ref_stg_merchants_history_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `fct_application` | `unique_fct_application_application_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `fct_installment_status` | `assert_fifo_no_skipped_installments` | singular | consistency | error | ✅ pass |
| silver/core | `fct_installment_status`, `dm_loan_delinquency_snapshot` | `assert_snapshot_dpd_matches_installments` | singular | accuracy | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_accepted_range_fct_installment_status_amount_due__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_accepted_range_fct_installment_status_days_past_due__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_accepted_range_fct_installment_status_paid_amount__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_accepted_range_fct_installment_status_remaining_amount__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_is_overdue_due_date_as_of_date_and_not_is_settled_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_is_settled_remaining_amount_0_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_is_settled_settled_date_is_not_null_` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_not_is_fpd30_eligible_or_is_first_installment` | generic: expression_is_true | validity | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_not_is_fpd30_or_is_fpd30_eligible` | generic: expression_is_true | validity | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_not_is_overdue_or_days_past_due_0` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_paid_amount_amount_due` | generic: expression_is_true | accuracy | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_paid_amount_paid_amount_any` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_expression_is_true_fct_installment_status_settled_date_is_null_or_settled_date_as_of_date` | generic: expression_is_true | timeliness | error | ✅ pass |
| silver/core | `fct_installment_status` | `dbt_utils_unique_combination_of_columns_fct_installment_status_loan_id__installment_number` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/core | `fct_installment_status` | `not_null_fct_installment_status_as_of_date` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_installment_status` | `not_null_fct_installment_status_days_past_due` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_installment_status` | `not_null_fct_installment_status_due_date` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_installment_status` | `not_null_fct_installment_status_installment_sk` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_installment_status` | `not_null_fct_installment_status_loan_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_installment_status` | `not_null_fct_installment_status_paid_amount` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_installment_status` | `relationships_fct_installment_status_loan_id__loan_id__ref_fct_loan_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `fct_installment_status` | `unique_fct_installment_status_installment_sk` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `fct_loan` | `accepted_values_fct_loan_currency__COP__BRL` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `fct_loan`, `dm_loan_delinquency_snapshot` | `assert_snapshot_covers_every_valid_loan` | singular | completeness | error | ✅ pass |
| silver/core | `fct_loan` | `dbt_utils_accepted_range_fct_loan_fx_days_stale__5__0` | generic: accepted_range | timeliness | error | ✅ pass |
| silver/core | `fct_loan` | `dbt_utils_accepted_range_fct_loan_principal_usd__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/core | `fct_loan` | `dbt_utils_expression_is_true_fct_loan_disbursed_date_application_created_date` | generic: expression_is_true | timeliness | error | ✅ pass |
| silver/core | `fct_loan` | `dbt_utils_expression_is_true_fct_loan_first_due_date_disbursed_date` | generic: expression_is_true | timeliness | error | ✅ pass |
| silver/core | `fct_loan` | `dbt_utils_expression_is_true_fct_loan_n_installments_term_months` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `fct_loan` | `dbt_utils_expression_is_true_fct_loan_principal_approved_amount` | generic: expression_is_true | accuracy | error | ✅ pass |
| silver/core | `fct_loan` | `dbt_utils_expression_is_true_fct_loan_total_amount_due_principal` | generic: expression_is_true | accuracy | error | ✅ pass |
| silver/core | `fct_loan` | `not_null_fct_loan_application_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_loan` | `not_null_fct_loan_customer_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_loan` | `not_null_fct_loan_disbursed_date` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_loan` | `not_null_fct_loan_fx_units_per_usd` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_loan` | `not_null_fct_loan_loan_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_loan` | `not_null_fct_loan_merchant_sk` | generic: not_null | integrity | error | ✅ pass |
| silver/core | `fct_loan` | `not_null_fct_loan_person_sk` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_loan` | `not_null_fct_loan_principal_usd` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_loan` | `relationships_fct_loan_application_id__application_id__ref_fct_application_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `fct_loan` | `relationships_fct_loan_customer_id__customer_id__ref_stg_customers_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `fct_loan` | `relationships_fct_loan_merchant_sk__merchant_sk__ref_dim_merchant_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `fct_loan` | `relationships_fct_loan_person_sk__person_sk__ref_dim_customer_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `fct_loan` | `unique_fct_loan_application_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `fct_loan` | `unique_fct_loan_loan_id` | generic: unique | uniqueness | error | ✅ pass |
| silver/core | `fct_payment` | `accepted_values_fct_payment_currency__COP__BRL` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `fct_payment` | `accepted_values_fct_payment_source_system__legacy_v1__core_v2` | generic: accepted_values | validity | error | ✅ pass |
| silver/core | `fct_payment`, `fct_installment_status`, `fct_loan` | `assert_installment_paid_reconciles_with_payments` | singular | consistency | error | ✅ pass |
| silver/core | `fct_payment`, `stg_payments` | `assert_no_reversed_payment_in_fct_payment` | singular | accuracy | error | ✅ pass |
| silver/core | `fct_payment` | `dbt_utils_accepted_range_fct_payment_amount__False__0` | generic: accepted_range | validity | error | ✅ pass |
| silver/core | `fct_payment` | `dbt_utils_expression_is_true_fct_payment_loan_cumulative_paid_amount` | generic: expression_is_true | consistency | error | ✅ pass |
| silver/core | `fct_payment` | `dbt_utils_unique_combination_of_columns_fct_payment_loan_id__loan_payment_seq` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| silver/core | `fct_payment` | `not_null_fct_payment_amount` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_payment` | `not_null_fct_payment_amount_usd` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_payment` | `not_null_fct_payment_loan_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_payment` | `not_null_fct_payment_paid_date` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_payment` | `not_null_fct_payment_payment_id` | generic: not_null | completeness | error | ✅ pass |
| silver/core | `fct_payment` | `relationships_fct_payment_loan_id__loan_id__ref_fct_loan_` | generic: relationships | integrity | error | ✅ pass |
| silver/core | `fct_payment` | `unique_fct_payment_payment_id` | generic: unique | uniqueness | error | ✅ pass |
| gold | `agg_merchant_monthly` | `accepted_values_agg_merchant_monthly_merchant_category__HOME__HEALTH__FASHION__ELECTRONICS__MOTORCYCLES__EDUCATION__TRAVEL__UNKNOWN` | generic: accepted_values | validity | error | ✅ pass |
| gold | `agg_merchant_monthly`, `fct_application`, `fct_loan`, `dm_loan_delinquency_snapshot` | `assert_agg_merchant_monthly_reconciles` | singular | consistency | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_accepted_range_agg_merchant_monthly_approval_rate__1__0` | generic: accepted_range | validity | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_accepted_range_agg_merchant_monthly_fpd30_rate__1__0` | generic: accepted_range | validity | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_accepted_range_agg_merchant_monthly_gmv_usd__0` | generic: accepted_range | validity | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_accepted_range_agg_merchant_monthly_par30_rate__1__0` | generic: accepted_range | validity | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_expression_is_true_agg_merchant_monthly__disbursed_loans_0_gmv_usd_0_` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_expression_is_true_agg_merchant_monthly_applications_approved_applications` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_expression_is_true_agg_merchant_monthly_fpd30_loans_fpd30_eligible_loans_and_fpd30_eligible_loans_disbursed_loans` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_expression_is_true_agg_merchant_monthly_loans_par30_month_end_loans_with_balance_month_end` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_expression_is_true_agg_merchant_monthly_par30_usd_month_end_outstanding_usd_month_end_0_000001` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `agg_merchant_monthly` | `dbt_utils_unique_combination_of_columns_agg_merchant_monthly_merchant_id__month` | generic: unique_combination_of_columns | uniqueness | error | ✅ pass |
| gold | `agg_merchant_monthly` | `not_null_agg_merchant_monthly_merchant_category` | generic: not_null | completeness | error | ✅ pass |
| gold | `agg_merchant_monthly` | `not_null_agg_merchant_monthly_merchant_id` | generic: not_null | completeness | error | ✅ pass |
| gold | `agg_merchant_monthly` | `not_null_agg_merchant_monthly_merchant_sk` | generic: not_null | integrity | error | ✅ pass |
| gold | `agg_merchant_monthly` | `relationships_agg_merchant_monthly_merchant_id__merchant_id__ref_dim_merchant_` | generic: relationships | integrity | error | ✅ pass |
| gold | `agg_merchant_monthly` | `relationships_agg_merchant_monthly_merchant_sk__merchant_sk__ref_dim_merchant_` | generic: relationships | integrity | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `accepted_values_dm_loan_delinquency_snapshot_dpd_bucket__0__1_30__31_60__61_90__90_` | generic: accepted_values | validity | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `accepted_values_dm_loan_delinquency_snapshot_loan_status__SETTLED__CURRENT__DELINQUENT` | generic: accepted_values | validity | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_accepted_range_dm_loan_delinquency_snapshot_dpd__0` | generic: accepted_range | validity | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_accepted_range_dm_loan_delinquency_snapshot_outstanding_local__0` | generic: accepted_range | validity | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_accepted_range_dm_loan_delinquency_snapshot_outstanding_usd__0` | generic: accepted_range | validity | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_expression_is_true_dm_loan_delinquency_snapshot__dpd_0_n_overdue_0_` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_expression_is_true_dm_loan_delinquency_snapshot__loan_status_DELINQUENT_dpd_0_` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_expression_is_true_dm_loan_delinquency_snapshot__loan_status_SETTLED_outstanding_local_0_` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_expression_is_true_dm_loan_delinquency_snapshot_abs_outstanding_net_of_partial_local_paid_amount_total_amount_due_0_01` | generic: expression_is_true | accuracy | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_expression_is_true_dm_loan_delinquency_snapshot_dpd_bucket_case_when_dpd_0_then_0_when_dpd_30_then_1_30_when_dpd_60_then_31_60_when_dpd_90_then_61_90_else_90_end_` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_expression_is_true_dm_loan_delinquency_snapshot_is_par30_dpd_30_` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_expression_is_true_dm_loan_delinquency_snapshot_n_settled_n_partial_n_unpaid_n_installments_and_n_installments_term_months` | generic: expression_is_true | consistency | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `dbt_utils_expression_is_true_dm_loan_delinquency_snapshot_outstanding_net_of_partial_local_outstanding_local_and_overdue_amount_local_outstanding_local` | generic: expression_is_true | accuracy | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `not_null_dm_loan_delinquency_snapshot_as_of_date` | generic: not_null | completeness | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `not_null_dm_loan_delinquency_snapshot_dpd` | generic: not_null | completeness | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `not_null_dm_loan_delinquency_snapshot_fx_units_per_usd_at_snapshot` | generic: not_null | completeness | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `not_null_dm_loan_delinquency_snapshot_loan_id` | generic: not_null | completeness | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `not_null_dm_loan_delinquency_snapshot_outstanding_usd` | generic: not_null | completeness | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `relationships_dm_loan_delinquency_snapshot_loan_id__loan_id__ref_fct_loan_` | generic: relationships | integrity | error | ✅ pass |
| gold | `dm_loan_delinquency_snapshot` | `unique_dm_loan_delinquency_snapshot_loan_id` | generic: unique | uniqueness | error | ✅ pass |
| seed | `city_canonical` | `not_null_city_canonical_city_key` | generic: not_null | completeness | error | ✅ pass |
| seed | `city_canonical` | `not_null_city_canonical_city_name` | generic: not_null | completeness | error | ✅ pass |
| seed | `city_canonical` | `unique_city_canonical_city_key` | generic: unique | uniqueness | error | ✅ pass |
