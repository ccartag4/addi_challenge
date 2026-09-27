# Assumptions and Data Quality Findings — Data Challenge

Numbered so they can be referenced from models, tests, `RESULTS.md` and `DATA_QUALITY.md`.
Figures come from `evidence/bronze_profiling.md` (SQL over the bronze layer) unless noted.
Each finding is classified with a DAMA-DMBOK data quality dimension.

---

## A. Assumptions (business definitions and interpretation)

| # | Assumption | Rationale | Alternative considered |
|---|---|---|---|
| A1 | **A real person is identified by `document_number` alone.** | The data dictionary states it explicitly. | `document_number + country`: 346 of the 907 shared documents span CO and BR with different birth years (F13). Both counts are published in `RESULTS.md` Q7; the dictionary rule is the primary answer. |
| A2 | **An application's final state is its latest event by `event_at_utc`**, with `_ingested_at_utc` as tiebreaker and, for identical instants, `_op` order I < U < D. | The dictionary defines current state as the latest *version*; business time is the event time, ingest time only says when we saw it. | Latest by `_ingested_at_utc` (gives a different final status for 54 applications, per exploratory profiling; confirmed in staging tests). |
| A3 | **Any application with a `_op = 'D'` event is invalid** and excluded from every metric, together with its loans (none exist) and events. | Dictionary: a deleted application did not exist for business purposes. | None. |
| A4 | **`customer_id = 999999999` is a placeholder, not a customer.** It is treated as NULL, and an application's customer is the real `customer_id` seen on any of its events. | It is the only customer id absent from the master, appears on 1,353 events across CREATED/APPROVED/REJECTED and I/U/D, and 104 of its rows are exact twins of a real-customer row (F4). | Keep it as an unknown customer: would break referential integrity for 1,348 applications and mis-assign 325 loans whose latest event carries the placeholder. |
| A5 | **A valid loan** has an application that exists in the CDC, is not deleted, and whose final status is APPROVED. | Dictionary: loans without a valid application are corrupt migration records. | None. |
| A6 | **Every business date is the UTC timestamp converted to `America/Bogota`.** Disbursement month, payment date, application date and FX lookup date all use the Bogotá date. | README section 4.2. | UTC dates: shift 5,900 loans by a day and 171 by a month (exploratory profiling; re-measured in `dq_09`). |
| A7 | **FX rate for a date = last published rate on or before that date** (forward fill over a daily calendar). GMV uses the rate of the disbursement business date. | The provider publishes on business days only; 176 days per currency are missing (F12). | Backward fill or interpolation: not how treasury books a rate; forward fill is the standard "last known rate". |
| A8 | **`legacy_v1` amounts are in minor units for both COP and BRL and are divided by 100.** | Median settled payment ÷ median installment is 100.0 for legacy in both currencies and 1.0 for core_v2 (F9). | Apply the factor to one currency only, or use 1,000: contradicted by the measured ratio. |
| A9 | **An effective payment is a `SETTLED` row not referenced by any `REVERSED` row.** Reversal rows are never money; a payment reversed twice is excluded once. | Dictionary semantics of reversals; 5 payments are targeted by two reversal rows (F11). | Netting positive and negative amounts: double-subtracts those 5 payments and breaks the "one row per effective payment" grain. |
| A10 | **Payments duplicated by timestamp format are one payment.** Deduplication is on `payment_id` after parsing timestamps. | 666 `payment_id`s have two rows that differ only in the string format of the same instant (F3). | None. |
| A11 | *(pending, Phase 3)* Outstanding balance of a partially paid installment. | | |
| A12 | *(pending, Phase 3)* FX rate used for outstanding balance at the snapshot. | | |
| A13 | *(pending, Phase 4)* PAR30 per merchant-month: cohort view vs month-end series. | | |
| A14 | *(pending, Phase 4)* Date that assigns an application to a merchant category. | | |
| A15 | **Customer `created_at` is a calendar date stored as a midnight-UTC timestamp; the customer creation date is its UTC date, not the Bogotá conversion.** | All 30,000 values are at `00:00:00` (dq_09: 30,000 of 30,000 rows would shift a day under the Bogotá rule). Converting would date every customer one day earlier than the source shows. No metric in the challenge depends on this field. | Apply A6 uniformly: mechanically consistent but visibly wrong for a business user. |

---

## B. Data quality findings

| # | Source | Finding | DMBOK dimension | Treatment | Rows affected | Test / evidence |
|---|---|---|---|---|---|---|
| F1 | applications, loans, payments, customers | Timestamps arrive in three shapes: `YYYY-MM-DD HH:MM:SS`, ISO `…T…Z`, and 13-digit Unix epoch in milliseconds. | Validity | `parse_utc_ts` macro handles all three; anything else becomes NULL and is caught by a test. | apps event_at 106,268 / 15,530 / 6,399 · loans 23,278 / 3,357 / 1,440 · payments 93,040 / 13,574 / 5,725 · customers created_at 24,770 / 3,713 / 1,517 | `dq_01`; staging test: parsed timestamp not null where raw not null |
| F2 | applications, payments | Exact duplicate rows from dump reprocessing. | Uniqueness | `SELECT DISTINCT` in staging. | apps 4,984 · payments 1,537 | `dq_02` |
| F3 | payments | 666 `payment_id`s with two rows that differ only in `paid_at_utc` string format (same instant). | Uniqueness | Dedup on `payment_id` after timestamp parsing (A10). | 666 | `dq_02`, `dq_05` row 5; test `unique payment_id` on staging |
| F4 | applications | Placeholder `customer_id = 999999999` on 1,353 events of 1,348 applications; absent from the customer master; 104 rows are exact twins of a real-customer row at the same instant. | Validity, Integrity | Null the placeholder; resolve the application's customer from its other events (A4). | 1,353 rows · 1,348 applications · 104 twin rows | `dq_03` rows 13/17, `dq_07` rows 19/20; test: no placeholder in `fct_application` |
| F5 | applications | Deleted applications: 953 `D` rows on 941 applications, always the last event. | Timeliness, Validity | Exclude (A3). | 941 applications | `dq_03` rows 5/7; test: no deleted application in `fct_application` |
| F6 | applications | Event order and ingest order disagree for a small set of applications (late-arriving events). | Timeliness | Order by event time with ingest time as tiebreaker (A2). | 54 applications (exploratory; confirmed in staging) | singular test in Phase 3 |
| F7 | loans, installments | 120 loans whose `application_id` does not exist in the CDC; the same 120 have no installments. | Integrity | Exclude as corrupt migration records (A5). | 120 | `dq_04` rows 6/14; `relationships` test loan → application |
| F8 | loans | Loan attributes agree with the originating application: customer (once the placeholder is removed), merchant, currency, and principal = approved amount for every loan. | Consistency, Accuracy | Keep as enforced tests, they protect the join. | 0 mismatches | `dq_04` rows 8–11; Phase 3 singular test |
| F9 | payments | `legacy_v1` reports amounts in minor units: median payment ÷ median installment = 100.0 for COP and BRL; core_v2 = 1.0. | Accuracy | Divide legacy amounts by 100 (A8). | 21,022 legacy rows | `dq_05` rows 18–21 |
| F10 | payments | `legacy_v1` loan references carry an `LN-` prefix; core_v2 uses the bare id. | Validity | Extract trailing digits as `loan_id`. | 21,022 | `dq_05` row 7; test: every payment's loan exists |
| F11 | payments | 1,296 `REVERSED` rows, each with the negative of its target amount, same source system, no dangling targets; 5 targets reversed by two rows. | Accuracy, Uniqueness | Exclude reversal rows and their targets (A9). | 1,296 reversal rows · 5 double reversals | `dq_05` rows 9–15; singular test: no reversed payment in `fct_payment` |
| F12 | fx_rates | 176 missing days per currency between 2024-12-23 and 2026-08-14: 170 weekend days and 6 holidays (2025-01-01, 2025-04-18, 2025-12-25, 2026-01-01, 2026-04-03, 2026-05-01). | Completeness | Daily calendar with forward fill (A7). | 176 per currency | `dq_06`; test: no loan without a rate |
| F13 | customers | 30,000 `customer_id`s but 29,093 distinct documents: 907 redundant ids. Of the 907 shared documents, 346 span two countries, 886 have different birth years, only 4 share an email. | Uniqueness | Person grain on `document_number` (A1); collisions flagged in a column. | 907 | `dq_07` rows 3–8; test `unique document_number` on `dim_customer` |
| F14 | customers | Free-text hygiene: `monthly_income` has `-1` sentinels (858) and thousands separators; `birth_year = 1900` on 63 rows; every email needs lower/trim; city has 14 raw spellings for 11 places. | Validity | Sentinels → NULL, numeric parsing, lower/trim, accent-insensitive title case. | see `dq_07` | `dq_07` rows 11–18 |
| F15 | merchants_history | 162 of 700 merchants have a second version: 157 category changes, 72 name changes that are only casing/spaces, 0 country changes. | Consistency | SCD2 with `valid_to = next valid_from − 1 day`; normalized name. | 162 | `dq_08`; test: no overlapping validity ranges |
| F16 | installments | Plan is internally consistent: installment count equals `term_months` for every loan, no non-positive amounts, due dates 2025-02-02 to 2027-06-30 (many not yet due at the snapshot). | Accuracy | Enforce as tests. | 0 anomalies | `dq_04` rows 15–18 |

---

## C. Out of scope and how I would solve it

*(to be completed at the end)*
