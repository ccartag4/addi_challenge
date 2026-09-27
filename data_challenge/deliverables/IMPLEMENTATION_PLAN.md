# Implementation Plan — Data Challenge (Lumo lending warehouse)

> Evidence document. Written **before** the first line of code, on 2026-09-26, after reading the
> assessment, the challenge README, the data dictionary, and profiling the seven raw extracts.
> It records the approach, the decisions taken (with the questions that led to them), and the
> step-by-step plan that `WORKLOG.md` will later trace commit by commit.

---

## 1. Goal and grading lens

Build a dbt Bronze → Silver → Gold model over Lumo's lending extracts and answer seven business
questions with defensible figures. The assessment makes three things explicit:

1. **Judgment over tooling.** The AI log is graded. Every decision must be explainable in the
   follow-up conversation.
2. **Verifiable numbers.** Reviewers may not run the pipeline. `RESULTS.md` plus committed run
   output must let them check every figure without re-executing.
3. **Flawless core beats broad scope.** Anything out of reach goes to `ASSUMPTIONS.md` with how it
   would have been solved.

Time budget for this challenge: roughly 6 to 6.5 hours of hands-on work.

---

## 2. Working method

| Practice | How it is applied |
|---|---|
| **Human runs, AI explains** | David executes every command himself. The AI assistant provides the goal, the exact command, and what to look for in the output. Nothing advances until the output is understood. |
| **AI drafts, human approves** | SQL models, YAML and macros are drafted by the AI assistant, then reviewed line by line before they run. This is the AI usage the assessment expects, and each approval or correction feeds `AI_LOG.md`. |
| **One step, one worklog entry, one commit** | `WORKLOG.md` gets one entry per step (template below). Each step closes with a conventional commit (`feat(bronze): …`, `test(silver): …`, `docs: …`). |
| **AI log fed in real time** | When the AI produces something wrong or incomplete, it is recorded in `AI_LOG.md` at that moment, with how it was caught and fixed. |
| **Data quality framed with DAMA-DMBOK** | See section 4. Each dbt test carries a `meta.dq_dimension`; each finding in `ASSUMPTIONS.md` is classified by dimension; a `DATA_QUALITY.md` matrix is generated at the end. |
| **Reproducibility first** | Local DuckDB, pinned Python and package versions, a three-command README, and the final `dbt build` output committed to the repo. |

### Worklog entry template

```
## Step NN — <title>  (YYYY-MM-DD HH:MM)
Goal:        what this step is for
Command(s):  exact command(s) executed
Result:      what came back (row counts, pass/fail, timings)
Finding / decision: what was learned or decided, and why
DMBOK dimension:    dimension affected, if any
Commit:      <hash> <message>
```

---

## 3. Decision log — questions asked and answers given

These four questions were raised by the AI assistant before starting, because each one changes
the shape of the work. Answers were given by David on 2026-09-26.

| # | Question | Options offered | Decision | Rationale |
|---|---|---|---|---|
| 1 | Which engine do we build the dbt project on? | DuckDB local (recommended) · Databricks · Snowflake | **DuckDB local** | Zero accounts and cost, runs the ~130k-row tables in seconds, and a reviewer can reproduce every number with three commands. Explicitly allowed by the README ("any other data lake / local dbt setup"). |
| 2 | Where will the repository live? | Copy to `C:\dev` and start a clean repo (recommended) · Stay in OneDrive · Existing repo | **Copy to `C:\dev\addi_ai_amplifier_tech_challenge`, new `git init`** | Git inside OneDrive causes file locks and sync conflicts on `.git`. A stray, commit-less git repo was also found at the user's home directory and must not be confused with the submission repo. |
| 3 | "DAMA-DMBOK" for quality documentation: how deep? | Full (recommended) · Light · Something else | **Full** | Tests tagged with their DMBOK dimension, findings classified by dimension, plus a `DATA_QUALITY.md` matrix. Turns the test suite into a data-governance narrative rather than a loose list. |
| 4 | Language of the deliverables? | English (recommended) · Spanish · Mixed | **English** | Matches the language of the assessment and the READMEs. Working conversation stays in Spanish. |

Additional environment decisions taken at the same time:

- **Python 3.12 in an isolated `uv` virtual environment.** The machine's default Python is 3.14 and
  dbt support for it is uncertain.
- **Layer naming.** `models/bronze/` (raw copies, all columns as text), `models/silver/staging/`
  (typed, parsed, exact-deduplicated), `models/silver/intermediate/` (business logic),
  `models/silver/core/` (`dim_*`, `fct_*`), `models/gold/` (`agg_*`, `dm_*`).
- **Raw ingestion.** Sources point directly at the CSV files using DuckDB's `read_csv` with
  `all_varchar=true`, so no type is coerced before the staging layer decides how.
- **Parameters as dbt vars.** `snapshot_date = 2026-06-30` and `cutover_date = 2025-07-01` are
  variables, never literals inside models.

Open item: the exact submission deadline (five calendar days from receipt) is pending
confirmation and decides how much of Phase 6 is attempted.

---

## 4. DAMA-DMBOK data quality framework

The dimensions used, and the kind of check that lands in each one:

| Dimension | Meaning here | Example checks in this project |
|---|---|---|
| **Completeness** | Required values are present | `not_null` on grain keys; FX rate present for every disbursement date |
| **Uniqueness** | One record per real-world entity | `unique` on `loan_id`, `payment_id`; one person per `document_number` |
| **Validity** | Values conform to format and domain | `accepted_values` on status, currency, `_op`, source system; timestamps parse under all three formats |
| **Accuracy** | Values reflect the real fact | Legacy amounts rescaled to major units; principal equals approved amount |
| **Consistency** | Same fact agrees across sources | Loan customer/merchant/currency agree with the originating application |
| **Integrity** (referential) | Relationships resolve | `relationships` tests loan → application, payment → loan, installment → loan |
| **Timeliness / currency** | Data is current and correctly ordered in time | CDC final state by event time, not ingest time; no legacy payments after cutover |

Every dbt test declares `meta: {dq_dimension: <dimension>}`. `DATA_QUALITY.md` is built from
`manifest.json` and `run_results.json` at the end and lists, per model, each dimension, its tests,
their status and the related finding number in `ASSUMPTIONS.md`.

---

## 5. Known data traps the plan must handle

Found during profiling on 2026-09-26. Figures are from an exploratory pandas pass and will be
re-derived in SQL during Phase 1; they are anchors, not answers.

| Area | Finding | Planned treatment | DMBOK dimension |
|---|---|---|---|
| Timestamps | Three formats across four files: `YYYY-MM-DD HH:MM:SS`, ISO with `Z`, 13-digit epoch milliseconds | One parsing macro applied in staging | Validity |
| Applications CDC | 4,984 exact duplicate rows; 941 applications end in `_op = 'D'`; 54 applications where ordering by event time vs ingest time yields a different final status | Exact dedup; latest version by `event_at_utc` with `_ingested_at_utc` as tiebreaker; any `D` invalidates the application | Uniqueness, Timeliness |
| Loans | 120 loans whose application does not exist in the CDC; 325 loans whose `customer_id` differs from the application's | Exclude orphans; origination is source of truth for customer | Integrity, Consistency |
| Time zone | 5,900 loans change calendar day in Bogotá; 171 change month | Convert to `America/Bogota` before deriving any business date | Accuracy |
| FX rates | No weekend rates; 6 weekday holidays missing; 7,607 loans disbursed on weekends | Daily calendar spine with forward-fill of the last published rate | Completeness |
| Payments | `legacy_v1` amounts are 100× the installment size in both currencies and use `LN-` refs; 1,537 exact duplicates; 666 `payment_id`s duplicated only by timestamp format | Divide legacy by 100; strip prefix; dedup on `payment_id` after parsing | Accuracy, Uniqueness |
| Reversals | Reversal rows carry the negative of the target amount; 5 payments reversed twice; 2 payments after the snapshot date | Effective payment = `SETTLED` and not referenced by any reversal; never net amounts | Accuracy |
| Customers | 30,000 ids, 29,093 distinct documents (907 redundant ids); 346 documents shared across CO and BR with different birth years; one `customer_id` referenced by 1,353 application events missing from the master | Person key = `document_number` as the dictionary states; publish the alternative count; flag collisions and the missing id | Uniqueness, Integrity |
| Merchants | 162 of 700 merchants have a second version; names change casing | SCD2 with `valid_to = LEAD(valid_from) - 1 day`; join events on date ranges; normalize names | Consistency |

Definitions the README leaves open, to be fixed and documented in `ASSUMPTIONS.md`:

1. Outstanding balance of a partially paid installment (plan: full `amount_due`, per README wording).
2. FX rate for outstanding balance at the snapshot (plan: snapshot-date rate; alternative documented).
3. PAR30 per merchant per month: true month-end series vs cohort-as-of-cutoff (plan: cohort view).
4. Which date assigns an application to a merchant category (plan: first event date in Bogotá; disbursement date for loans).

---

## 6. Step-by-step plan

| Phase | Content | Estimate |
|---|---|---|
| 0 | Repository, Python environment, worklog | 30 min |
| 1 | dbt project, bronze, SQL profiling | 1 h |
| 2 | Macros and staging | 1 h |
| 3 | Intermediate, dimensions and facts | 2 h to 2.5 h |
| 4 | Gold and documentation | 1 h |
| 5 | Results, cross-verification, write-ups | 1 h |
| 6 | Optional extras | remaining time |

### Phase 0 — Preparation
1. Copy the inner challenge folder to `C:\dev\addi_ai_amplifier_tech_challenge`. `git init`, add a `.gitignore` (`target/`, `dbt_packages/`, `logs/`, `*.duckdb`, `.venv/`, `.DS_Store`, `__MACOSX/`). Initial commit with the untouched challenge files.
2. Create `WORKLOG.md` and the skeletons of `AI_LOG.md` and `ASSUMPTIONS.md`.
3. Create the environment: `uv venv --python 3.12`, install `dbt-core`, `dbt-duckdb`, `duckdb`, `pandas`; freeze versions to `requirements.txt`.
4. Verify with `dbt --version`.

### Phase 1 — dbt project and Bronze
5. Hand-write `dbt_project.yml` and `profiles.yml` inside `deliverables/` (use `DBT_PROFILES_DIR`). Declare schemas bronze/silver/gold and vars `snapshot_date`, `cutover_date`. Install `dbt_utils`.
6. `sources.yml` pointing at the seven CSVs via `read_csv(..., all_varchar=true, header=true)`.
7. Seven `brz_*` models as 1:1 copies with load metadata. `dbt debug`, `dbt run --select bronze`.
8. SQL profiling over bronze: date formats, duplicates, CDC operations, FX gaps, legacy amount scale. Each finding is numbered in `ASSUMPTIONS.md` with its DMBOK dimension.

### Phase 2 — Silver staging
9. Macros: `parse_utc_ts`, `to_bogota_date`, `clean_text`. Each verified with `dbt show` before use.
10. Seven `stg_*` models: casts, parsed timestamps, trims, exact deduplication. Generic tests (`not_null`, `accepted_values`, `unique`) tagged with dimensions.
11. `dbt build --select staging`. Commit.

### Phase 3 — Silver intermediate and core entities
12. CDC resolution → `fct_application` (latest by event time, tiebreak by ingest time, deleted excluded, `is_valid` flag).
13. `dim_merchant` SCD2 (`valid_from`, `valid_to`, `is_current`). Custom test: no overlapping ranges, exactly one current row per merchant.
14. `dim_customer` at person grain plus `bridge_customer_person` (customer_id → person_key). Cleaning rules for city, email, income, birth year.
15. `int_fx_daily` (calendar spine, forward-filled) → `fct_loan` with `principal_usd` at the disbursement-date rate. Custom test: no loan without a rate.
16. `fct_payment`: both sources normalized, legacy ÷ 100, `LN-` stripped, dedup on `payment_id`, reversed and reversal rows excluded. Custom tests: no reversed payment survives; no legacy payment after cutover; no double-counted reversal.
17. `int_installment_allocation` (FIFO via cumulative sums over installments and payments, no recursion) → `fct_installment_status` (paid amount, settled date, days past due). Tests: paid ≤ due; DPD ≥ 0; settled implies fully paid.

### Phase 4 — Gold
18. `dm_loan_delinquency_snapshot` as of `snapshot_date`: outstanding local and USD, DPD, bucket (`0`, `1-30`, `31-60`, `61-90`, `90+`). Tests: accepted buckets, non-negative outstanding.
19. `agg_merchant_monthly`: merchant × month, category as of the event date, applications, approval rate, GMV USD, disbursed loans, FPD30, PAR30. Tests: unique (merchant, month); rates within 0–1.
20. `schema.yml` with the grain in every model description and explanations for every non-trivial column. `dbt docs generate`.

### Phase 5 — Results and verification
21. One query per business question under `analyses/`, executed and exported to `results/*.csv`.
22. Independent cross-check with a pandas script; every difference explained or fixed; recorded in `AI_LOG.md` section 4.
23. Write `RESULTS.md`, `ASSUMPTIONS.md`, `DATA_QUALITY.md`, `AI_LOG.md`, `README.md` (three commands). Commit the final `dbt build` output.

### Phase 6 — Optional, if time remains
24. Incremental materialization for `fct_payment` with a late-arrival lookback; dbt snapshot for the merchant SCD2; contracts on gold models; exposures.

---

## 7. Definition of done

- `dbt build` passes with zero errors; every test carries a DMBOK dimension.
- Every model description starts with its grain.
- The seven answers in `RESULTS.md` name the model or query that produces them and match the committed `results/` exports.
- `AI_LOG.md` contains: what was delegated and what was not, 3–5 decisive prompts, at least two AI errors with how they were caught, and how the final numbers were verified.
- `WORKLOG.md` has one entry per step and each entry maps to a commit.
- The repository README lets a reviewer set up and build the project in three commands.
