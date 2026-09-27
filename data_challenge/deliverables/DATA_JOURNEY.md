# Data Journey — what happened to every row, and why

One place that answers three questions a reviewer asks: **how many rows went in and came out of
each layer, and why** (section A); **what happened at each step of the build** (section B); and
**every error met on the way, with its root cause** (section C). Section D lists conclusions that
changed as later layers revealed more.

Row counts in section A are produced by `analyses/profiling/dq_15_row_count_funnel.sql`
(evidence in `evidence/row_count_funnel.md`), not typed by hand. F-numbers are findings and
A-numbers are assumptions in `ASSUMPTIONS.md`; AI-numbers are cases in `AI_LOG.md`.
Updated at the end of every step.

---

## A. Row-count funnel per extract

### applications_cdc

| Layer | Rows | Δ | Why |
|---|---|---|---|
| bronze.brz_applications_cdc | 128,197 | | as delivered |
| silver.stg_applications_cdc | 121,087 | −7,110 | 4,984 exact duplicate rows (F2) + 2,126 same event delivered in two timestamp shapes (F3). Removed by `DISTINCT` on typed columns. |
| silver.int_application_events | 121,087 | 0 | ranks and flags added, nothing removed |
| silver.fct_application | 60,000 | grain change | 121,087 events → 60,000 applications, latest version by event time (A2). 1,353 events had the placeholder customer `999999999` nulled (F4, A4). |
| … where is_valid | 59,059 | −941 | applications with a CDC delete event (F5, A3) |
| … where is_approved | 33,007 | −26,052 | rejected applications; 0 remain undecided |

### loans

| Layer | Rows | Δ | Why |
|---|---|---|---|
| bronze.brz_loans | 28,075 | | as delivered |
| silver.stg_loans | 28,075 | 0 | no duplicates in this extract |
| silver.int_loan_validated | 28,075 | 0 | verdict and `exclusion_reason` added |
| silver.fct_loan | 27,955 | −120 | `NO_APPLICATION`: application id absent from the CDC (F7, A5). None deleted, none unapproved. |

Inside `fct_loan`: 8,223 loans (29.42 %) take a forward-filled FX rate (F12, A7); 325 loans get
their customer from the application because their latest CDC event carried the placeholder
(F4, A19); 237 loans sit on `UNKNOWN`-category merchant versions (F17, A17).

### installments

| Layer | Rows | Δ | Why |
|---|---|---|---|
| bronze.brz_installments | 130,297 | | as delivered |
| silver.stg_installments | 130,297 | 0 | no duplicates; plan is internally consistent (F16) |
| … on valid loans | 130,297 | 0 | the 120 excluded loans have no installments at all |
| silver.int_payment_allocation | 114,347 | grain change | payment × installment pairs from FIFO (A21): 107,554 payments, 6,772 of them split across installments, 14,451 installments funded by several payments; 0 money left unallocated |
| silver.fct_installment_status | 130,297 | 0 | one row per installment as of 2026-06-30 (A20): 99,542 settled, 245 partial, 30,510 unpaid; 6,120 overdue; 24,821 first installments FPD30-eligible, 2,204 flagged (A23) |

### payments

| Layer | Rows | Δ | Why |
|---|---|---|---|
| bronze.brz_payments | 112,339 | | as delivered |
| silver.stg_payments | 110,136 | −2,203 | 1,537 exact duplicate rows (F2) + 666 same payment in two timestamp shapes (F3) |
| silver.int_payment_classified | 110,136 | 0 | classified: EFFECTIVE 107,554 · REVERSED_OUT 1,291 · REVERSAL_ROW 1,291 |
| … where EFFECTIVE | 107,554 | −2,582 | 1,291 reversal rows + the 1,291 payments they void (F11, A9) |
| silver.fct_payment | 107,554 | 0 | no effective payment sits on an invalid loan |

Inside `fct_payment`: every `legacy_v1` amount divided by 100 (F9, A8) and every `LN-` reference
normalized (F10); 1 payment is dated after the snapshot and is kept for gold to filter.

### customers

| Layer | Rows | Δ | Why |
|---|---|---|---|
| bronze.brz_customers | 30,000 | | as delivered |
| silver.stg_customers | 30,000 | 0 | 858 `-1` and 1,505 `N/A` incomes and 63 birth years of 1900 nulled (A16); 14 city spellings keyed |
| silver.bridge_customer_person | 30,000 | 0 | one row per customer_id, mapped to its person |
| silver.dim_customer | 29,093 | −907 | redundant customer_ids collapse into people by `document_number` (F13, A1); 346 people flagged cross-country, 884 with conflicting birth years |

### merchants_history

| Layer | Rows | Δ | Why |
|---|---|---|---|
| bronze.brz_merchants_history | 862 | | as delivered |
| silver.stg_merchants_history | 862 | 0 | names keyed (72 casing variants, F15) |
| silver.dim_merchant | 862 | 0 | one row per version; 16 missing categories imputed: 5 carried forward, 11 `UNKNOWN` (F17, A17) |
| … where is_current | 700 | −162 | second versions closed with `valid_to` (157 category changes, 5 name-only) |

### fx_rates

| Layer | Rows | Δ | Why |
|---|---|---|---|
| bronze.brz_fx_rates | 848 | | as delivered, business days only |
| silver.stg_fx_rates | 848 | 0 | |
| silver.int_fx_daily | 1,200 | +352 | daily calendar 2024-12-23 → 2026-08-14 × 2 currencies; 176 missing days per currency filled (170 weekend + 6 holidays, F12, A7) |
| … where is_published | 848 | −352 | the fill is tagged, never confused with a published rate |

---

## B. Step by step: what was built, what the data showed, why, what was decided

| Step (commit) | Built | What the data or the tool showed | Root cause | Decision | Errors on the way | Evidence |
|---|---|---|---|---|---|---|
| 00 (—) | environment diagnosis | `uv` missing; Python 3.14 / 3.13 / 3.11; empty git repo in the home folder | plan written before checking the machine | `venv` with Python 3.13, no extra tool | none | WORKLOG 00 |
| 01 · 01b (`efad48f`, `70e5728`, `7f4d813`) | clean repo in `C:\dev`, `.gitignore`, first commits | first commit had 44 files: a nested copy of the 22 originals | `Copy-Item -Recurse` ran twice; when the destination exists it copies *inside* it | compared both copies by SHA-256 (0 differences), removed the nested one, fixed forward instead of rewriting history | duplicate noticed only after the push, through `git ls-files` | WORKLOG 01, 01b |
| 02 (`2cb78e0`) | WORKLOG, AI_LOG, ASSUMPTIONS skeletons | — | — | records exist before any model, so evidence is captured as it happens | none | — |
| 03 (`431860a`) | Python environment | dbt-core 1.12.5, dbt-duckdb 1.11.0, duckdb 1.5.5, pandas 3.0.6 | — | full freeze pinned; written as ASCII because PowerShell 5.1 `>` writes UTF-16 | none | requirements.txt |
| 04 · 04b (`431860a`, `eb5f0d0`, `2c982f0`) | `dbt_project.yml`, `profiles.yml`, `dbt_utils`, schema-name macro | `.user.yml` (dbt telemetry id) appeared in the commit | `.gitignore` drafted without knowing dbt's first-run side effects | ignored, `git rm --cached`, telemetry disabled | AI 3.2; `git rm` path given relative to repo root while the shell was in `deliverables/` | WORKLOG 04, 04b |
| 05 · 05b (`2c72ff5`, `b28e3a2`) | sources on the CSVs, 7 bronze views, 10 tests | all 7 row counts equal the README; 10 deprecation warnings | test `meta` must live under `config` since dbt 1.10 | pattern `config: {meta: {dq_dimension: …}}` adopted for every layer | AI 3.3 | WORKLOG 05 |
| 06 (`06efbb1`, `b0f71eb`) | 8 profiling analyses, Markdown export script | 3 timestamp shapes; 4,984 / 1,537 exact duplicates; 666 format duplicates; 941 deletes; placeholder customer on 1,353 events; legacy amounts ×100; 1,296 reversal rows; 176 FX days missing per currency; 907 redundant customer ids; 162 merchant versions | see F1–F16 | A1–A10 and F1–F16 written | `--select "dq_*"` selects no analyses; the scratch check had passed on stale compiled files (AI 3.4) | evidence/bronze_profiling.md |
| 07 (`c726edf`) | macros `parse_utc_ts`, `to_business_date`, text helpers; dq_09 | 0 parse failures on 4 columns; 5,900 loans change day and 171 change month in Bogotá; all 30,000 customer `created_at` at 00:00 UTC; session `TimeZone` = America/Bogota | `to_timestamp()::timestamp` applies the session zone (−5 h) silently | `epoch_ms()` for epochs; A15 keeps customer creation as a UTC date | none: the zone trap was pre-empted and evidenced | evidence/timestamp_parsing.md |
| 08 (`cc91de4`) | 7 staging views, 43 tests | applications 121,087 (2,126 more format duplicates than expected); payments 110,136; 27 deprecation warnings | test parameters must live under `arguments:` (dbt ≥ 1.10) | `DISTINCT` on typed columns; sentinels nulled (A16); placeholder flagged, not dropped | AI 3.5 | WORKLOG 08 |
| 09 (`82b6e34`) | `int_application_events`, `fct_application`, first singular test | 60,000 applications: 941 deleted, 59,059 valid, 33,007 approved (55.8882 %); 54 change status under ingest ordering; 3 valid ones have no real customer | late-arriving events (F6); placeholder-only applications (F4) | A2 ordering by business time; the 3 kept with a flag and a warn-level test | none | evidence/cdc_resolution.md |
| 10 (`fc3eb49`) | `dim_merchant` SCD2, 3 singular tests | `not_null` on category failed with 16 rows; 8.16 % of applications would change category under a "current" lookup | profiling counted distinct values, not NULLs; `accepted_values` ignores NULLs | A17: carry forward (5) or `UNKNOWN` (11) with `category_source` / `category_imputation`; NULL counts added to dq_08 | AI 3.6 | evidence/merchant_profiling.md, scd2_merchant.md |
| 11 (`10bf1f9`) | `dim_customer`, `bridge_customer_person`, city seed, 2 singular tests | 29,093 people, 907 redundant ids, 346 cross-country, 884 conflicting birth years; alternative identity 29,439 / 561 | people onboarded more than once; the source captured different attributes each time | A1 identity by document, A18 latest record, flags instead of filters, canonical cities as a seed | none | evidence/customer_identity.md |
| 12 (`c483994`) | `int_fx_daily`, `int_loan_validated`, `fct_loan`, 2 singular tests | 1,200-day FX calendar; 27,955 valid loans; GMV 8,780,942.16 USD, equal to the independent pandas pass to the cent; 8,223 loans on days with no published rate; 2026-01 cohort 1,540 loans / 473,272.15 USD | provider publishes on business days; loans are disbursed every day | A7 forward fill with source date and staleness on every row; A19 customer from the application | none | evidence/loans_gmv.md |
| 13 (`a81377a`) | `int_payment_classified`, `fct_payment`, 3 singular tests | 107,554 effective payments; 1,291 reversal rows void exactly 1,291 payments; legacy closed on Bogotá time, core opened on UTC midnight (F18); 1 payment after the snapshot | the "5 double reversals" of raw profiling were reversal rows delivered in two formats (F3) | A9 by set membership, unaffected; F11 reworded; cutover test | binder error: a test referenced a CTE column that was not projected; one-line fix | evidence/payments_effective.md |
| 13b (`f8e26ee`) | `DATA_JOURNEY.md`, `dq_15_row_count_funnel` | 30 funnel rows; every delta maps to a finding or assumption; FX calendar 1,200 rows of which 848 published | — | row-level accounting maintained at every step | none | evidence/row_count_funnel.md |
| 14 (*pending*) | `int_payment_allocation`, `fct_installment_status`, 4 singular tests | 114,347 allocation pairs, 0 unallocated money; 99,542 / 245 / 30,510 installments settled / partial / unpaid as of the snapshot; FPD30 8.8796 % global and 7.7922 % for 2026-01; preview PAR30 20.5008 % on 2,069,175.39 USD outstanding | payments arrive at loan level; FIFO by interval overlap reproduces the README rule without recursion | A11, A12, A20–A23; full-history allocation, as-of cut in the fact | a leftover placeholder line in the fact's select list was removed before the first build | evidence/fifo_and_delinquency.md |

---

## C. Error ledger

| # | Step | Symptom | Class | Root cause | Fix | Reference |
|---|---|---|---|---|---|---|
| E1 | pre-repo | exploratory profiling reported 6,399 unparseable application timestamps and 1,440 loans "outside the FX range" | AI | 13-digit epoch-millisecond values not recognised by a generic parser | explicit epoch branch; both symptoms vanished | AI 3.1 |
| E2 | 01 | nested duplicate of all challenge files in the first commit | process | `Copy-Item -Recurse` executed twice | `git rm -r` of the nested copy, new commit | WORKLOG 01b |
| E3 | 04 | `.user.yml` committed | AI / tool | `.gitignore` drafted without dbt's first-run side effects | ignore, untrack, disable telemetry | AI 3.2 |
| E4 | 04b | `fatal: pathspec … did not match` | AI | path relative to repo root while the shell was in `deliverables/` | rerun from the right folder | WORKLOG 04b |
| E5 | 05 | `PropertyMovedToConfigDeprecation` ×10 | AI (stale syntax) | test `meta` outside `config` | moved under `config` | AI 3.3 |
| E6 | 06 | `does not match any enabled nodes`; scratch validation had passed | AI / process | name wildcards do not select analyses; validation not from a clean state | `path:` selector; clean-state rule for every later check | AI 3.4 |
| E7 | 08 | `MissingArgumentsPropertyInGenericTestDeprecation` ×27 | AI (stale syntax) | test parameters outside `arguments:` | moved under `arguments:` | AI 3.5 |
| E8 | 10 | `not_null_dim_merchant_category` FAIL 16 | data + AI | 16 versions without category; profiling had no NULL counts; `accepted_values` ignores NULLs | A17 imputation with audit columns; NULL counts in dq_08 | AI 3.6, F17 |
| E9 | 13 | `Binder Error: Referenced column "reversal_amount_total" not found` | AI | column computed in a CTE, not projected | added to the select list | WORKLOG 13 |
| W1 | 09 → | standing warning: 3 valid applications without a real customer | data | every event of those applications carries the placeholder id | kept with `has_unresolved_customer`, warn-level test by design | F4, A4 |

---

## D. Conclusions revised as later layers revealed more

| First conclusion (where) | Revised conclusion (where) | Why it changed |
|---|---|---|
| 5 payments reversed twice (dq_05, raw profiling) | 0 double reversals: 1,291 reversal rows void 1,291 payments (dq_14, after staging) | the 5 were the same reversal row in two timestamp formats (F3); A9 was already implemented by set membership, so no logic changed |
| 4,984 duplicate CDC rows (dq_02) | 7,110 rows removed at staging (dq_15) | 2,126 additional events are identical once timestamps are parsed (F3); invisible to a string-level comparison |
| 886 people with conflicting birth years (dq_07) | 884 (dq_12) | birth year 1900 is a sentinel (A16); two conflicts existed only against that sentinel |
| 104 placeholder twin rows (raw) | 146 (after parsing) | more twins become visible once both rows share a parsed timestamp (F4) |
