# Worklog — Data Challenge

Step-by-step trace of how the solution was built. One entry per step; each entry maps to a
commit. The plan these steps follow is in `IMPLEMENTATION_PLAN.md`.

---

## Step 00 — Environment diagnosis  (2026-09-26)

**Goal:** confirm available tooling before creating the repository and the Python environment.

**Command(s):**
```powershell
uv --version
py -0p
Test-Path C:\Users\david\.git; git -C C:\Users\david log --oneline -3
```

**Result:**
- `uv` is not installed.
- Installed Pythons: 3.14 (default), 3.13, 3.11.
- A git repository exists at the user's home directory with no commits (accidental `git init`).

**Finding / decision:** the plan assumed `uv` with Python 3.12. Changed to the standard-library
`venv` with Python 3.13, which is already installed and supported by current dbt releases. This
avoids installing an extra tool. The stray home-directory repository is empty and unrelated to
the submission; it is left untouched.

**DMBOK dimension:** n/a (environment).

**Commit:** none (read-only step).

---

## Step 01 — Clean repository outside OneDrive  (2026-09-26)

**Goal:** copy the inner challenge folder to `C:\dev`, initialise git, and record the untouched
original materials as the first commit.

**Command(s):**
```powershell
Copy-Item -Recurse "<OneDrive>\addi_ai_amplifier_tech_challenge\addi_ai_amplifier_tech_challenge" "C:\dev\addi_ai_amplifier_tech_challenge"
Get-ChildItem C:\dev\addi_ai_amplifier_tech_challenge -Recurse -Force -Filter .DS_Store | Remove-Item -Force
git init -b main
# .gitignore created (Python, dbt artefacts, *.duckdb, OS files)
git add . ; git reset -q data_challenge/deliverables/IMPLEMENTATION_PLAN.md
git commit -m "chore: import original challenge materials (untouched)"
git add data_challenge/deliverables/IMPLEMENTATION_PLAN.md
git commit -m "docs(data): add implementation plan and decision log"
git remote add origin https://github.com/ccartag4/addi_challenge.git
git push -u origin main
```

**Result:** push succeeded, but the first commit contained 44 files instead of 22.

**Finding / decision:** verification after the push (`git ls-files`) showed a nested
`addi_ai_amplifier_tech_challenge/` folder holding a second copy of every challenge file.
Root cause: `Copy-Item -Recurse` was executed twice. When the destination folder already exists,
PowerShell copies the source folder *inside* it instead of merging. The copy command is not
idempotent. All nested files were compared by SHA-256 against the root copies: 0 differences.
Fixed in step 01b.

**DMBOK dimension:** Uniqueness (duplicated records at file level). A small preview of the same
class of problem the raw extracts have.

**Commits:** `efad48f` chore: import original challenge materials (untouched) ·
`70e5728` docs(data): add implementation plan and decision log

---

## Step 01b — Remove duplicated nested copy  (2026-09-26)

**Goal:** remove the duplicated folder without losing any original file.

**Command(s):**
```powershell
git rm -r -q addi_ai_amplifier_tech_challenge
git commit -m "fix: remove duplicated nested copy of challenge materials"
git push
```

**Result:** 22 files removed; 23 files tracked (21 challenge files, the plan, `.gitignore`).
Remote `main` updated `70e5728..7f4d813`.

**Finding / decision:** fixed forward with a new commit rather than rewriting history with a
force push. Safer on a shared remote, and it keeps an honest record of the error and its fix.

**DMBOK dimension:** Uniqueness.

**Commit:** `7f4d813` fix: remove duplicated nested copy of challenge materials

---

## Step 02 — Worklog, AI log and assumptions skeletons  (2026-09-26)

**Goal:** create the three running records before any modelling starts, so evidence is captured
as it happens.

**Files:** `WORKLOG.md`, `AI_LOG.md`, `ASSUMPTIONS.md`. `IMPLEMENTATION_PLAN.md` updated for the
`venv` / Python 3.13 decision.

**Commit:** `2cb78e0` docs(data): add worklog, AI log and assumptions skeletons

---

## Step 03 — Python environment with dbt  (2026-09-27)

**Goal:** isolated environment inside `deliverables/` with pinned versions, so a reviewer
installs exactly the same stack.

**Command(s):**
```powershell
cd data_challenge\deliverables
py -3.13 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install dbt-duckdb pandas
pip freeze | Out-File -Encoding ascii requirements.txt
dbt --version
```

**Result:**

| Package | Version |
|---|---|
| Python | 3.13.13 |
| dbt-core | 1.12.5 |
| dbt-duckdb | 1.11.0 |
| duckdb | 1.5.5 |
| pandas | 3.0.6 |

62 packages pinned in `requirements.txt`. `.venv/` confirmed ignored by git
(`git check-ignore`).

**Finding / decision:** `requirements.txt` written with `Out-File -Encoding ascii` because
PowerShell 5.1's `>` operator writes UTF-16, which is unreliable for `pip install -r`. The full
freeze is committed, not just top-level packages, so transitive dependencies are reproducible
too.

**DMBOK dimension:** n/a (environment).

**Commit:** `431860a` (together with step 04)

---

## Step 04 — dbt project configuration  (2026-09-27)

**Goal:** project ready to connect to DuckDB, with the medallion layers declared and business
parameters held as variables.

**Files:** `dbt_project.yml`, `profiles.yml`, `packages.yml`, `package-lock.yml`,
`macros/generate_schema_name.sql`.

**Command(s):**
```powershell
dbt deps
dbt debug
git add . ; git commit -m "build(data): add dbt project config, duckdb profile and dbt_utils"
git push
```

**Result:** `dbt_utils` installed; `dbt debug` → `All checks passed!`, connection OK;
`lumo.duckdb` created and ignored by git.

**Key decisions:**
- Bronze and staging materialised as **views** (read and clean only, no data duplication);
  intermediate, core and gold as **tables** (heavy logic such as FIFO, queried often).
- Business parameters as `vars`: `raw_data_path`, `snapshot_date = 2026-06-30`,
  `cutover_date = 2025-07-01`, `business_tz = America/Bogota`. No model hard-codes them.
- `store_failures: true` into a `dq_audit` schema: every failed test leaves its offending rows
  queryable, which backs the DMBOK findings with evidence.
- `generate_schema_name` override so schemas are exactly `bronze`, `silver`, `gold`,
  `dq_audit` instead of dbt's default `main_bronze`, etc.
- `profiles.yml` lives in the project folder; dbt reads it from the working directory, so a
  reviewer needs no local configuration.

**Finding / decision:** the commit unexpectedly included `.user.yml`, dbt's anonymous telemetry
id created on first run. Fixed in step 04b. Logged as AI error 3.2 in `AI_LOG.md`.

**DMBOK dimension:** n/a (configuration).

**Commit:** `431860a` build(data): add dbt project config, duckdb profile and dbt_utils

---

## Step 04b — Remove `.user.yml` and disable telemetry  (2026-09-27)

**Goal:** keep machine-specific files out of the repository and stop sending usage telemetry.

**Command(s):**
```powershell
git rm --cached data_challenge/deliverables/.user.yml
git add .gitignore data_challenge/deliverables
git commit -m "chore(data): ignore dbt .user.yml and disable anonymous telemetry"
git push
```

**Result:** first attempt committed the `.gitignore`, telemetry flag and log updates
(`eb5f0d0`), but `git rm --cached` failed with "pathspec did not match": the path was given
relative to the repository root while the shell was inside `deliverables/`. `.user.yml` stayed
tracked. Second attempt from `deliverables/` with `git rm --cached .user.yml` removed it.

**Finding / decision:** git pathspecs resolve against the current directory, not the repo root.
Small AI slip, worth noting because the same mistake inside a dbt `read_csv` path would have
been silent rather than loud.

**DMBOK dimension:** n/a (configuration / data handling).

**Commits:** `eb5f0d0` chore(data): ignore dbt .user.yml and disable anonymous telemetry ·
`2c982f0` chore(data): untrack dbt .user.yml

---

## Step 05 — Sources and Bronze layer  (2026-09-27)

**Goal:** declare the seven CSVs as dbt sources read straight from disk with every column as
text, and expose them as 1:1 bronze views with a grain declared on each.

**Files:** `models/bronze/sources.yml`, seven `brz_*.sql`, `models/bronze/bronze.yml`.

**Command(s):**
```powershell
dbt run --select bronze
dbt test --select bronze
dbt show --inline "<row counts per bronze view>"
```

**Result (validated beforehand in a scratch copy of the project, then reproduced here):**

| Bronze view | Rows | README says |
|---|---|---|
| brz_applications_cdc | 128,197 | ~128k |
| brz_loans | 28,075 | ~28k |
| brz_installments | 130,297 | ~130k |
| brz_payments | 112,339 | ~112k |
| brz_customers | 30,000 | 30k |
| brz_merchants_history | 862 | ~860 |
| brz_fx_rates | 848 | ~850 |

10 completeness tests on identifier columns: all pass. Schemas created: `bronze`, `dq_audit`.

**Key decisions:**
- Sources use dbt-duckdb's `external_location` with a `read_csv(..., all_varchar=true)` call.
  No copy of the raw files is made and no type is inferred; bronze shows the data exactly as
  delivered, which is what a Bronze layer is for.
- `raw_data_path` is a project var, so the same project runs against another folder with
  `--vars` and no code change.
- Each bronze view adds `_brz_source_file` and `_brz_built_at` for lineage.
- Bronze tests only assert identifier presence (completeness). Uniqueness and validity are
  deliberately *measured* in step 06 and *enforced* from staging, because bronze must keep the
  duplicates so they can be counted and documented.
- `store_failures` creates one table per test under `dq_audit`, empty when the test passes.

**DMBOK dimension:** completeness (tests); the layer itself is the baseline for every other
dimension.

**Commit:** `2c72ff5` feat(bronze): declare raw CSV sources and 1:1 bronze views with grain and
completeness tests

---

## Step 05b — Fix deprecated test syntax  (2026-09-27)

**Goal:** remove the `PropertyMovedToConfigDeprecation` warning (10 occurrences) raised by the
bronze run.

**Finding / decision:** `dbt parse --no-partial-parse` shows the cause: since dbt 1.10, `meta`
on a data test is no longer a top-level property and must live under `config:`. The AI drafted
the pre-1.10 form. Fixed in `bronze.yml`:

```yaml
- not_null:
    config:
      meta: {dq_dimension: completeness}
```

This matters beyond the warning: `DATA_QUALITY.md` will be generated from the manifest, and in
the new form the dimension lands in `config.meta`, which is where the generator will read it.
Logged as AI error 3.3.

**Command(s):**
```powershell
dbt parse --no-partial-parse      # zero deprecation warnings expected
dbt test --select bronze          # still PASS=10
```

**DMBOK dimension:** n/a (tooling).

**Commit:** `b28e3a2` fix(bronze): move test meta under config per dbt 1.10+ and log the
correction (also carries the first version of the profiling analyses and the export script)

---

## Step 06 — SQL profiling of the raw extracts  (2026-09-27)

**Goal:** measure, in SQL over bronze, every anomaly the staging layer will have to handle, and
leave the measurements as committed evidence that `ASSUMPTIONS.md` can cite by number.

**Files:** eight analyses under `analyses/profiling/` (`dq_01` … `dq_08`), one per DMBOK
question; `scripts/run_analyses.py`, which executes compiled analyses against the warehouse
read-only and writes full Markdown tables (`dbt show` truncates cells to 20 characters, so it
is not usable as evidence).

| Analysis | Question it answers | DMBOK dimension |
|---|---|---|
| dq_01_timestamp_formats | Which date/time shapes does each column contain? | Validity |
| dq_02_duplicates | Exact duplicate rows and duplicate keys per extract | Uniqueness |
| dq_03_cdc_applications | CDC operations, statuses, deletes, same-instant events | Timeliness, Validity |
| dq_04_loans_integrity | Loans vs applications vs installments | Integrity, Consistency |
| dq_05_payments | Two sources, reference formats, amount scale, reversals | Accuracy, Uniqueness |
| dq_06_fx_gaps | Missing days in the FX calendar, weekend vs weekday | Completeness |
| dq_07_customers | Person vs customer_id, free-text hygiene, missing references | Uniqueness, Integrity |
| dq_08_merchants | Versions per merchant, what changes, name hygiene | Consistency |

**Command(s):**
```powershell
dbt compile --select "path:analyses/profiling"
python scripts/run_analyses.py --pattern "dq_*" --out evidence/bronze_profiling.md --title "Bronze profiling — raw extract data quality"
```

**Incident:** the command first handed over was `dbt compile --select "dq_*"`, which dbt
answered with "does not match any enabled nodes". Name wildcards select models but not
analyses; `path:` or `resource_type:analysis` do. The AI had "validated" the command in a
scratch project where earlier `dbt show` calls had already compiled the analyses, so the export
script found files and the check passed for the wrong reason. Logged as AI error 3.4.

**Result:** eight analyses, 118 measurements, written to `evidence/bronze_profiling.md`.
Headline figures (details and dimensions in `ASSUMPTIONS.md` section B):

| Measurement | Value |
|---|---|
| Timestamp shapes per column | 3 (plain, ISO-Z, epoch ms) |
| Exact duplicate rows | apps 4,984 · payments 1,537 |
| Payment ids duplicated by timestamp format only | 666 |
| Deleted applications | 941 |
| Placeholder customer id `999999999` | 1,353 events · 1,348 applications |
| Loans without application / without installments | 120 / 120 |
| legacy_v1 amount ÷ installment | 100.0 (COP and BRL) |
| Reversal rows / payments reversed twice | 1,296 / 5 |
| FX missing days per currency | 176 = 170 weekend + 6 holidays |
| Redundant customer ids | 907 (346 cross-country) |
| Merchants with a second version | 162 (157 category changes) |

**Finding / decision:** one finding was new relative to the exploratory pandas pass: the
applications with more than one `customer_id` (1,345) and the single customer id missing from
the master (1,353 CDC rows) are the same phenomenon. A follow-up query showed the id is
`999999999`, a placeholder present on every operation and status; 104 of its rows are exact
twins of a real-customer row at the same instant, which is what `dq_02` reported as key
duplicates. Decision A4: treat it as NULL and resolve the customer from the application's other
events. Positive findings (F8, F16: principal = approved amount, installment count = term) are
kept as enforced tests because they protect the joins.

**DMBOK dimensions covered:** validity, uniqueness, completeness, accuracy, consistency,
integrity, timeliness.

**Commit:** `06efbb1` docs(data): add SQL profiling evidence of the raw extracts and log selector fix

---

## Step 06b — Findings written to ASSUMPTIONS.md  (2026-09-27)

**Goal:** turn the measurements into numbered, citable assumptions (A1–A10 decided, A11–A14
pending) and findings (F1–F16) with DMBOK dimension, treatment and the test that will enforce
each one.

**Commit:** *(filled after commit)*

---

## Step 07 — Macros: timestamp parsing, business time, text hygiene  (2026-09-27)

**Goal:** one place for the three transformations every staging model needs, each verified
before use.

**Files:** `macros/parse_utc_ts.sql`, `macros/business_time.sql`, `macros/text_helpers.sql`,
`analyses/profiling/dq_09_timestamp_parsing.sql`.

| Macro | Does | Finding / assumption |
|---|---|---|
| `parse_utc_ts(col)` | Three raw shapes → naive UTC `TIMESTAMP`; anything else → NULL | F1 |
| `to_business_ts` / `to_business_date` | UTC → `America/Bogota` wall-clock / date, zone from `vars.business_tz` | A6 |
| `clean_text`, `normalize_key`, `parse_number` | Trim/collapse whitespace, accent-insensitive upper key, thousands-separator-safe numeric cast | F14, F15 |

**Command(s):**
```powershell
dbt compile --select dq_09_timestamp_parsing
python scripts/run_analyses.py --pattern "dq_09*" --out evidence/timestamp_parsing.md --title "Timestamp parsing coverage and Bogota date shifts"
```

**Result:**

| Column | Rows | Parse failures | Day shifts in Bogotá | Month shifts |
|---|---|---|---|---|
| applications_cdc.event_at_utc | 128,197 | 0 | 26,860 | 889 |
| loans.disbursed_at_utc | 28,075 | 0 | 5,900 | 171 |
| payments.paid_at_utc | 112,339 | 0 | 24,393 | 766 |
| customers.created_at | 30,000 | 0 | 30,000 | 991 |

**Finding / decision:**
- **Epoch parsing must use `epoch_ms()`, not `to_timestamp()::timestamp`.** Hand check on this
  machine: DuckDB's session `TimeZone` is `America/Bogota`, and
  `to_timestamp(1778106658000/1000.0)::timestamp` returns `2026-05-06 17:30:58` while
  `epoch_ms(1778106658000)` returns `2026-05-06 22:30:58`. The cast through TIMESTAMPTZ applies
  the local zone and would have shifted 13,564 epoch values by five hours with no error.
- **Customer `created_at` is a date at midnight UTC** (every one of the 30,000 rows would move
  a day under the Bogotá rule). Recorded as A15: creation date = UTC date.
- Bogotá conversion verified: `2026-01-01 03:00:00` UTC → `2025-12-31 22:00:00` local.

**DMBOK dimension:** validity (parsing), accuracy (time zone).

**Commit:** `c726edf` feat(macros): add utc timestamp parsing, business time and text helpers
with parsing evidence

---

## Step 08 — Silver staging layer  (2026-09-27)

**Goal:** seven typed, deduplicated staging views, one per extract, with the raw anomalies
(F1–F3, F9, F10, F14, F15) resolved and business rules (A2–A9) deliberately *not* applied yet.

**Files:** `models/silver/staging/stg_*.sql` (7), `models/silver/staging/staging.yml`,
`placeholder_customer_id` var in `dbt_project.yml`, `normalize_key` macro tightened to
alphanumerics only.

**Command(s):**
```powershell
dbt build --select "path:models/silver/staging"     # run + 43 tests
dbt parse --no-partial-parse                         # zero deprecation warnings expected
```

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Model | Rows | vs bronze | Why |
|---|---|---|---|
| stg_applications_cdc | 121,087 | −7,110 | 4,984 exact duplicates + 2,126 same-event-two-formats (F2, F3) |
| stg_loans | 28,075 | 0 | |
| stg_installments | 130,297 | 0 | |
| stg_payments | 110,136 | −2,203 | 1,537 exact duplicates + 666 format duplicates (F2, F3) |
| stg_customers | 30,000 | 0 | |
| stg_merchants_history | 862 | 0 | |
| stg_fx_rates | 848 | 0 | |

43 staging tests pass (uniqueness, completeness, validity, accuracy). Sanity checks:
1,353 placeholder-customer rows flagged; 63 birth years and 2,363 incomes nulled (A16);
10 city keys for 9 cities; 700 merchant name keys for 700 merchants.

**Key decisions:**
- Staging is where *typing* happens and nothing else: the placeholder customer is nulled and
  flagged but the row stays; deleted events stay with `cdc_op = 'D'`; reversal rows stay with
  `is_reversal = true`. Each business rule is then one explicit, testable step downstream.
- `DISTINCT` is applied on the *typed* projection, which is what makes the two-formats
  duplicates collapse: 2,126 CDC rows and 666 payments that a string-level dedup would keep.
- `stg_payments.amount` is already in major units for both sources (A8) so no downstream model
  ever sees `amount_raw` semantics.
- New deprecation caught (`MissingArgumentsPropertyInGenericTestDeprecation`, 27 tests):
  parameters moved under `arguments:`. Logged as AI error 3.5.

**DMBOK dimension:** validity, uniqueness, completeness, accuracy.

**Commit:** `cc91de4` feat(staging): typed and deduplicated silver staging views with 43
DMBOK-tagged tests

---

## Step 09 — CDC resolution: int_application_events → fct_application  (2026-09-27)

**Goal:** first business-rule model. Turn ~121k CDC events into one row per application in
its final state, applying A2 (ordering), A3 (deletes), A4 (placeholder customer) and A14
(creation date) as explicit, testable steps.

**Files:** `models/silver/intermediate/int_application_events.sql` (+ `intermediate.yml`),
`models/silver/core/fct_application.sql` (+ `core.yml`),
`tests/assert_deleted_applications_have_no_loans.sql` (first singular business test),
`analyses/profiling/dq_10_cdc_resolution.sql`.

**Design:** the intermediate model keeps the *event* grain and only adds window ranks
(`rn_event_desc`, `rn_ingest_desc`, `rn_event_asc`) and per-application flags
(`resolved_customer_id`, `application_deleted`). The fact model picks the rank-1 rows. This
split means any final state can be audited by looking at the ranked events, and a reviewer can
answer "why is this application REJECTED?" with one query.

**Command(s):**
```powershell
dbt build --select "path:models/silver" "path:tests"
dbt compile --select dq_10_cdc_resolution
python scripts/run_analyses.py --pattern "dq_10*" --out evidence/cdc_resolution.md --title "CDC resolution — applications in final state"
```

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| Applications in CDC | 60,000 |
| Deleted (A3) | 941 |
| Valid | 59,059 |
| Valid and approved | 33,007 |
| Valid and rejected | 26,052 |
| Valid still CREATED | 0 |
| Global approval rate | 55.8882 % |
| Final status differs if ordered by ingest time (F6) | 54, all valid |
| Valid applications with no real customer (F4 residue) | 3 |
| Events per application | 2 to 4, mean 2.02 |

68 tests: 67 pass, 1 warn (the 3-application residue, configured as `severity: warn` on
purpose and documented in F4). The singular test `assert_deleted_applications_have_no_loans`
passes with 0 rows.

**Finding / decision:**
- F6 is now measured exactly: 54 applications would carry a different final status under
  ingest-time ordering. All 54 are valid, so the choice in A2 changes Q1 by up to 54 counts.
- The A4 residue is 3 valid applications whose only events carry the placeholder. They keep
  `customer_id = NULL` and `has_unresolved_customer = true` rather than being dropped: they are
  real applications with a real merchant and decision, only the customer link is unknown.
- `created_date` starts on 2024-12-31 although the earliest UTC event is 2025-01-01: the first
  events of the year happen before 05:00 UTC and belong to the previous Bogotá day (A6).

**DMBOK dimension:** timeliness (A2, F6), validity (A3), integrity (A4, singular test).

**Commit:** `82b6e34` feat(silver): resolve application CDC into fct_application with
business-rule tests

---

## Step 10 — dim_merchant (SCD type 2)  (2026-09-27)

**Goal:** turn the append-only merchant history into a slowly changing dimension with
`valid_from`, `valid_to`, `is_current`, safe for point-in-time joins (A14).

**Files:** `models/silver/core/dim_merchant.sql`, `core.yml` (dim_merchant block), singular
tests `assert_dim_merchant_one_current_version`, `assert_dim_merchant_no_overlapping_versions`,
`assert_every_application_matches_one_merchant_version`,
`analyses/profiling/dq_11_scd2_merchant.sql`, `dq_08` extended with NULL counts.

**Command(s):**
```powershell
dbt build --select "path:models/silver" "path:tests"
dbt compile --select dq_08_merchants dq_11_scd2_merchant
python scripts/run_analyses.py --pattern "dq_08*" --out evidence/merchant_profiling.md --title "Merchant history profiling (with NULL counts)"
python scripts/run_analyses.py --pattern "dq_11*" --out evidence/scd2_merchant.md --title "SCD2 merchant dimension — verification"
```

**Incident:** the first build failed on `not_null_dim_merchant_category` with 16 rows. The
profiling analysis had summarised categories by distinct value (7 categories summing to 846 of
862 rows) and staging's `accepted_values` ignores NULLs, so the gap surfaced only at the
dimension. Logged as AI error 3.6 and finding F17; `dq_08` now reports NULLs per column.

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| Version rows / merchants / current rows | 862 / 700 / 700 |
| Merchants with 2 versions | 162 = 157 category changes + 5 name-only changes |
| Versions with missing category (F17) | 16: 5 carried forward, 11 UNKNOWN (A17) |
| Valid applications matched to exactly one version | 59,059 of 59,059 |
| Applications whose as-of category differs from the current one | 4,822 (8.16 %) |
| Merchant 1607 (largest by GMV) | one version, EDUCATION, BR |

85 tests: 84 pass, 1 warn (the known A4 residue). The three singular tests pass with 0 rows.

**Key decisions:**
- `valid_to` is NULL for the current version (dbt snapshot convention) and
  `valid_to_effective = 9999-12-31` exists for `BETWEEN` joins, so callers never write
  `coalesce` themselves.
- The point-in-time rule is not optional: 8.16 % of valid applications would be reported under
  the wrong category if the current one were used. That figure is the answer to "why SCD2?".
- Category gaps are filled transparently (A17): `category_source` keeps the raw value,
  `category_imputation` names the rule, and a consistency test ties the two together.
- `merchant_name_current` gives one display name per merchant for rankings (names only vary by
  casing, F15).

**DMBOK dimension:** consistency (SCD2 integrity tests), completeness (F17), integrity
(point-in-time coverage test).

**Commit:** `fc3eb49` feat(silver): add SCD2 dim_merchant with category gap handling and
point-in-time tests

---

## Step 11 — dim_customer (person grain) and bridge_customer_person  (2026-09-27)

**Goal:** one row per real person (A1) with the collapse from customer_ids fully auditable,
plus a bridge so facts keep their source customer_id and still roll up to people.

**Files:** `models/silver/core/dim_customer.sql`, `models/silver/core/bridge_customer_person.sql`,
`core.yml` (two new blocks), `seeds/city_canonical.csv` + `seeds/seeds.yml`, singular tests
`assert_bridge_covers_every_customer_id` and `assert_person_counts_reconcile`,
`analyses/profiling/dq_12_customer_identity.sql`.

**Command(s):**
```powershell
dbt build                                   # seeds + models + tests, whole project
dbt compile --select dq_12_customer_identity
python scripts/run_analyses.py --pattern "dq_12*" --out evidence/customer_identity.md --title "Customer identity — customer_ids vs real people"
```

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| customer_ids / real people / redundant ids (Q7) | 30,000 / 29,093 / 907 |
| Max customer_ids per person | 2 |
| People whose ids span two countries | 346 |
| People whose ids carry different birth years | 884 |
| Alternative identity document + country: people / redundant | 29,439 / 561 |
| People by canonical city | 9 cities, Bogotá D.C. largest with 7,760 |
| City keys outside the seed | 0 |

Full project build: 19 models, 1 seed, 106 tests → 125 pass, 1 warn (known A4 residue).
Both reconciliation tests pass with 0 rows.

**Key decisions:**
- Golden record = most recently created customer record (A18); everything older stays
  reachable via the bridge and the `customer_ids` list, so the collapse destroys nothing.
- Cross-country and birth-year conflicts are *flags*, not filters. The dictionary's identity
  rule is followed, and the alternative count is published next to it in Q7 rather than
  silently chosen.
- Canonical city names live in a seed, not in a CASE expression: reviewable as data, and a new
  spelling fails the `relationships` test instead of leaking through.
- Facts will keep `customer_id`; `bridge_customer_person` provides the person roll-up. This
  avoids rewriting keys inside facts and keeps every fact row traceable to its source record.

**DMBOK dimension:** uniqueness (person grain), integrity (bridge coverage), consistency
(count reconciliation), validity (city seed).

**Commit:** *(filled after commit)*
