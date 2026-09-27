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
| silver.int_loan_month_end_status | 264,143 | grain change | loan × month end from disbursement to the snapshot month (A13); 125,521 loan-months carry a balance; at 2026-06-30 identical to the snapshot loan by loan |

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
| silver.fct_installment_status | 130,297 | 0 | one row per installment as of 2026-06-30 (A20): 99,542 settled, 245 partial, 30,510 unpaid; 5,935 past due (A24); 24,821 first installments FPD30-eligible, 2,204 flagged (A23) |
| gold.dm_loan_delinquency_snapshot | 27,955 | grain change | installments → loans: 18,890 settled, 6,208 current, 2,857 delinquent; outstanding 2,069,175.39 USD, PAR30 20.5008 % (A11, A12) |

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
| gold.agg_merchant_monthly | 13,299 | grain change | 700 merchants × 19 months (dense grid, A13/A25): 11,327 rows with activity, 153 with a category change inside the month, 209 under UNKNOWN; totals reconcile to the facts on 8 measures |

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
| 14 (`04c92bb`) | `int_payment_allocation`, `fct_installment_status`, 4 singular tests | 114,347 allocation pairs, 0 unallocated money; 99,542 / 245 / 30,510 installments settled / partial / unpaid as of the snapshot; FPD30 8.8796 % global and 7.7922 % for 2026-01; preview PAR30 20.5008 % on 2,069,175.39 USD outstanding | payments arrive at loan level; FIFO by interval overlap reproduces the README rule without recursion | A11, A12, A20–A23; full-history allocation, as-of cut in the fact | a leftover placeholder line in the fact's select list was removed before the first build | evidence/fifo_and_delinquency.md |
| 15 (`c487dd6`) | `dm_loan_delinquency_snapshot` (first gold model), 2 singular tests | 27,955 loans: 18,890 settled, 6,208 current, 2,857 delinquent; outstanding 2,069,175.39 USD; PAR30 20.5008 %; sensitivities move PAR30 by < 0.1 pp; PAR30 77.88 % on 2025 loans vs 6.43 % on 2026 loans | a gold consistency test failed on 164 loans whose only unpaid installment was due exactly on the snapshot date: "overdue" had been written with ≤ while DPD counts days after the due date | A24 overdue = strictly past due; A11 gross balance, A12 snapshot rate, alternatives published as columns | AI 3.7: definitional boundary caught by a cross-model test | evidence/delinquency_snapshot.md |
| 16 (`699b3b0`) | `int_loan_month_end_status`, `agg_merchant_monthly`, 2 singular tests | 264,143 loan-months; 13,299 merchant-months; every business question reproduced from the aggregate; PAR30 rises monotonically 0 % → 20.5 % (no write-offs); FPD30 stable 7.8–9.6 % by cohort; top 5 merchants = 39.63 % of GMV, 1607 alone 23.49 %; without 1607 FPD30 8.64 % and PAR30 20.21 % | PAR30 is a stock, FPD30 a cohort; grain merchant × month needs one category per row | A13 month-end PAR30 with cohort variant as secondary column; A25 category at month end with change flag | category-change flag over-counted 14 first-month rows (NULL compared with `is distinct from`); fixed, 153 remain | evidence/merchant_monthly.md |
| 17 (`577c7cd`) | full column documentation of gold, 2 exposures, `DATA_QUALITY.md` generator, dbt artefacts and build log under `evidence/` | 244 tests: 243 pass, 1 warn; 30 of 30 models covered; 0 tests without a DMBOK dimension; 7 dimensions | documentation and artefacts are the reviewer's substitute for re-running | matrix generated from manifest + run_results, never hand-written; exposures for the Risk and Merchant consumers | YAML: five descriptions with `: ` in a plain scalar broke the parse; a failed build left an empty run_results that made the matrix report "not run" | DATA_QUALITY.md, evidence/dbt_artifacts/ |
| 18 (`10e27f7`) | 8 result queries under `analyses/results/`, `scripts/crosscheck_pandas.py` | every business question answered from gold/silver; independent pandas recomputation from the raw CSVs (own parser, own CDC resolution, FIFO as a per-loan loop in integer cents) matches on 24 of 24 checks, including DPD and balance on all 27,955 loans | two implementations of A1–A25 must agree for the numbers to be defensible | figures published in RESULTS.md only after the cross-check | share columns halved by a window over a `rollup` total (presentation bug, caught by reading); `float * Decimal` at the DuckDB boundary | evidence/results.md, evidence/crosscheck_pandas.md |
| 19 (`7d63f48`) | `RESULTS.md`, `README.md`, AI_LOG §1–2, ASSUMPTIONS §C, plan status; fresh-clone run of the three README commands | seven answers published with their producing query, sensitivities and interpretation; the README's three commands verified on a fresh clone | reviewers must be able to verify without re-running, and to re-run without configuring | figures published only after the 24/24 cross-check; open items listed with how they would be solved | — | RESULTS.md, README.md |
| 19b (*pending*) | `ARCHITECTURE.md` (Mermaid diagrams, requirement map), repository-root `README.md`, dependency split into `requirements.txt` + `requirements-lock-py313.txt` | the committed freeze did not install on Python 3.11 (`networkx==3.7`); top-level pins resolve on macOS, Linux and Windows for 3.11–3.13; the exact lock's wheels exist on macOS/Linux for 3.13; Python 3.11 executed end to end on Windows (PASS=273, 24/24) | a `pip freeze` records one machine; cross-platform claims need platform-targeted checks | two dependency files with explicit scope; README states executed vs resolved combinations | false alarm from a binary-only check on a pure-Python sdist; Windows long-path failure in the scratch folder | README.md, WORKLOG 19b |

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
| E10 | 15 | gold test `(dpd > 0) = (n_overdue > 0)` FAIL 164 | AI (definition) | `is_overdue` used `due_date <= as_of_date`; DPD counts days after the due date, so installments due on the snapshot date were "overdue with 0 days" | overdue = strictly past due (A24); invariant `is_overdue ⇒ days_past_due > 0` added | AI 3.7 |
| E11 | 19b | the committed `pip freeze` did not install on Python 3.11 (`networkx==3.7` requires 3.12+); a first cross-platform check also flagged a pure-Python sdist-only package as unavailable | AI / process | a freeze records one machine; the binary-only check could not see sdists | top-level pins in `requirements.txt`, exact set kept in `requirements-lock-py313.txt`; resolution verified per OS and Python with `uv pip compile` | AI 3.8 |
| W1 | 09 → | standing warning: 3 valid applications without a real customer | data | every event of those applications carries the placeholder id | kept with `has_unresolved_customer`, warn-level test by design | F4, A4 |

---

## D. Conclusions revised as later layers revealed more

| First conclusion (where) | Revised conclusion (where) | Why it changed |
|---|---|---|
| 5 payments reversed twice (dq_05, raw profiling) | 0 double reversals: 1,291 reversal rows void 1,291 payments (dq_14, after staging) | the 5 were the same reversal row in two timestamp formats (F3); A9 was already implemented by set membership, so no logic changed |
| 4,984 duplicate CDC rows (dq_02) | 7,110 rows removed at staging (dq_15) | 2,126 additional events are identical once timestamps are parsed (F3); invisible to a string-level comparison |
| 886 people with conflicting birth years (dq_07) | 884 (dq_12) | birth year 1900 is a sentinel (A16); two conflicts existed only against that sentinel |
| 104 placeholder twin rows (raw) | 146 (after parsing) | more twins become visible once both rows share a parsed timestamp (F4) |
| 6,120 installments overdue as of the snapshot (dq_16, step 14) | 5,935 (dq_16 after step 15) | 185 installments due exactly on 2026-06-30 were counted as overdue with 0 days past due; A24 makes "overdue" start the day after the due date. PAR30 and FPD30 unchanged. |
