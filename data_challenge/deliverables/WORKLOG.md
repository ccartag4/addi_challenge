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

**Commit:** `10bf1f9` feat(silver): add person-grain dim_customer, customer bridge and
canonical city seed

---

## Step 12 — FX daily calendar and fct_loan with USD  (2026-09-27)

**Goal:** a gap-free daily FX calendar with auditable forward fill (A7), an intermediate that
gives every delivered loan a verdict and a reason (A5), and the loan fact with USD amounts,
the SCD2 merchant version at disbursement and the resolved customer.

**Files:** `models/silver/intermediate/int_fx_daily.sql`, `int_loan_validated.sql`
(+ `intermediate.yml`), `models/silver/core/fct_loan.sql` (+ `core.yml`), singular tests
`assert_fx_daily_calendar_is_complete`, `assert_loan_agrees_with_application`,
`analyses/profiling/dq_13_loans_gmv.sql`.

**Command(s):**
```powershell
dbt build
dbt compile --select dq_13_loans_gmv
python scripts/run_analyses.py --pattern "dq_13*" --out evidence/loans_gmv.md --title "Loans, FX fill and GMV in USD"
```

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| Loans delivered / excluded / valid (Q2) | 28,075 / 120 (all `NO_APPLICATION`) / 27,955 |
| Total GMV in USD (Q2) | 8,780,942.16 |
| GMV by currency (USD) | COP 5,266,459.97 · BRL 3,514,482.19 |
| Cohort 2026-01 (Q3) | 1,540 loans · 473,272.15 USD (1,541 loans if UTC months were used) |
| Loans disbursed on a day with no published rate | 8,223 (29.42 %), max staleness 3 days |
| Loans matched to a merchant version at disbursement | 27,955 of 27,955 (237 on UNKNOWN category) |
| Top 5 merchants by GMV (Q6 preview) | 1607 BR EDUCATION 23.49 % · 1397 · 1664 · 1030 · 1286; top 5 = 39.63 %, top 20 = 53.86 % |
| Days application → disbursement | 0 to 7, median 4 |

Full project: 22 models, 1 seed, 142 tests → 164 pass, 1 warn (known A4 residue). The GMV
total matches the independent pandas pass from 2026-09-26 to the cent.

**Key decisions:**
- The FX calendar is a model, not a join-time trick: `rate_source_date` and `days_stale`
  travel to every loan, so "which rate did this USD figure use?" has an answer per row. Without
  the fill, 29.42 % of loans would have no USD value.
- `int_loan_validated` keeps all 28,075 loans with `exclusion_reason`; `fct_loan` is the
  filtered view the README asks for. A consistency test ties `is_valid` to the reason.
- `principal_usd` keeps 6 decimals; rounding happens only in gold/RESULTS, so sums reconcile
  with an independent computation.
- Merchant version and customer are resolved here once (A14, A19), so gold models never
  repeat point-in-time logic.

**DMBOK dimension:** completeness (FX calendar), accuracy (USD conversion, principal =
approved amount), consistency (loan vs application), integrity (application, customer,
merchant version links), timeliness (dates ordering, staleness bound).

**Commit:** `c483994` feat(silver): add forward-filled FX calendar, loan validation and
fct_loan with USD

---

## Step 13 — fct_payment: effective payments net of reversals  (2026-09-27)

**Goal:** one row per effective payment (A9) on a valid loan, normalized across the two
processors (A8, F10), with the ordering columns the FIFO allocation will need.

**Files:** `models/silver/intermediate/int_payment_classified.sql` (+ `intermediate.yml`),
`models/silver/core/fct_payment.sql` (+ `core.yml`), singular tests
`assert_no_reversed_payment_in_fct_payment`, `assert_payment_counts_reconcile`,
`assert_payment_sources_respect_cutover`, `analyses/profiling/dq_14_payments_effective.sql`.

**Command(s):**
```powershell
dbt build
dbt compile --select dq_14_payments_effective
python scripts/run_analyses.py --pattern "dq_14*" --out evidence/payments_effective.md --title "Payments - from delivered rows to effective payments"
```

**Incident:** first scratch build failed with `Binder Error: Referenced column
"reversal_amount_total" not found`: the AI wrote a test against a column it had computed in a
CTE but forgotten to project. One-line fix; noted here rather than in the AI log because the
tool caught it immediately and no wrong number was ever produced.

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| Payment rows: delivered / after dedup | 112,339 / 110,136 |
| By class | EFFECTIVE 107,554 · REVERSED_OUT 1,291 · REVERSAL_ROW 1,291 |
| Effective payments in `fct_payment` | 107,554 (0 on invalid loans) |
| By source | core_v2 87,129 · legacy_v1 20,425 |
| Amount received (local) | COP 20,096,349,720.00 · BRL 17,216,166.82 |
| Amount received (USD at payment-date rate) | 7,839,742.28 |
| Cutover boundary (F18) | legacy last: 2025-06-30 Bogotá (03:03 UTC 1 Jul) · core first: 00:04 UTC 1 Jul (30 Jun Bogotá) |
| Payments dated after the snapshot | 1 |
| Payments per valid loan | 0 to 18, median 4 · 2,240 loans with none yet · 18,890 at or above plan total · 0 overpaid |
| Legacy scale check after ÷100 | median payment / median installment = 1.0 |

Full project: 24 models, 1 seed, 164 tests → 188 pass, 1 warn (known A4 residue).

**Finding / decision:**
- **A profiling conclusion was refined.** Raw profiling reported 5 payments "reversed twice".
  After typed deduplication (F3) those are the same reversal row in two timestamp formats:
  1,291 reversal rows void exactly 1,291 payments. F11 and A9 were reworded. The design does
  not change because A9 was implemented as set membership, not as signed netting, so it is
  correct either way; the reconciliation test counts *distinct* voided payments for the same
  reason.
- Legacy and core closed on different clocks (F18). Not a defect to fix, but a fact that the
  cutover test now guards.
- `loan_payment_seq` and `loan_cumulative_paid` are computed once here; the FIFO step
  consumes them instead of re-deriving the order.

**DMBOK dimension:** accuracy (reversal exclusion, legacy scale), consistency (count
reconciliation), timeliness (cutover), integrity (loan link).

**Commit:** `a81377a` feat(silver): add fct_payment with reversal classification, cutover and
reconciliation tests

---

## Step 13b — DATA_JOURNEY.md: row-level accounting and step ledger  (2026-09-27)

**Goal:** a single document answering "how many rows went in and out of each layer, and why",
"what happened at each step" and "why did each error happen", so the explanation is not spread
across WORKLOG, ASSUMPTIONS and AI_LOG.

**Files:** `DATA_JOURNEY.md` (sections A funnel, B step ledger, C error ledger, D revised
conclusions), `analyses/profiling/dq_15_row_count_funnel.sql` (produces the funnel numbers so
section A is verifiable, not typed), `IMPLEMENTATION_PLAN.md` working-method table updated.

**Command(s):**
```powershell
dbt compile --select dq_15_row_count_funnel
python scripts/run_analyses.py --pattern "dq_15*" --out evidence/row_count_funnel.md --title "Row-count funnel per extract and layer"
```

**Result:** 30 funnel rows across the 7 extracts; every delta maps to a numbered finding or
assumption. Notable: the FX calendar has 1,200 rows (600 days × 2 currencies) of which 848 are
published; the 120 excluded loans have no installments, so all 130,297 installments belong to
valid loans.

**Decision:** maintained at the end of every step from here on, together with the worklog.

**Commit:** `f8e26ee` docs(data): add DATA_JOURNEY with row-count funnel, step ledger and error ledger

---

## Step 14 — FIFO allocation and fct_installment_status  (2026-09-27)

**Goal:** apply loan-level payments to installments FIFO (README 4.2) and state every
installment as of the snapshot: paid amount, settlement date, accrued days past due, FPD30
eligibility and flag.

**Files:** `models/silver/intermediate/int_payment_allocation.sql`,
`models/silver/core/fct_installment_status.sql`, `intermediate.yml` / `core.yml` blocks,
singular tests `assert_allocation_never_exceeds_payment`,
`assert_allocation_never_exceeds_installment`, `assert_fifo_no_skipped_installments`,
`assert_installment_paid_reconciles_with_payments`,
`analyses/profiling/dq_16_fifo_and_delinquency.sql`. Assumptions A11, A12, A20–A23 written.

**Design:** no recursion. Installments form consecutive intervals on a cumulative "debt line",
payments form consecutive intervals on a cumulative "money line" (running sums already in
`fct_payment`), and a payment funds an installment by the overlap of the two intervals. That is
FIFO by construction, it is one join, and every payment→installment pair is a row that can be
audited. The allocation is full-history; the fact applies the as-of cut by `paid_date`.

**Command(s):**
```powershell
dbt build
dbt compile --select dq_16_fifo_and_delinquency
python scripts/run_analyses.py --pattern "dq_16*" --out evidence/fifo_and_delinquency.md --title "FIFO allocation and installment status as of the snapshot"
```

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| Allocation rows (payment × installment) | 114,347 |
| Payments allocated / pure overpayment / unallocated excess | 107,554 / 0 / 0.00 in both currencies |
| Payments split across 2+ installments · installments funded by 2+ payments | 6,772 · 14,451 |
| Installments as of 2026-06-30: settled / partial / unpaid | 99,542 / 245 / 30,510 |
| Installments due / not yet due · overdue | 104,995 / 25,302 · 6,120 |
| Settled: early / on time / late 1–30 / late > 30 | 46,386 / 7,540 / 39,725 / 5,891 |
| Max days to settle · max accrued DPD | 70 · 512 |
| **FPD30 global (Q4)** | 2,204 / 24,821 = **8.8796 %** |
| **FPD30 cohort 2026-01 (Q4)** | 120 / 1,540 = **7.7922 %** |
| FPD30 flagged: unpaid vs paid late | 547 unpaid · 1,657 paid > 30 days late |
| Preview Q5 (mart built in step 15): loans with balance / fully settled | 9,065 / 18,890 |
| Preview Q5: outstanding USD at snapshot rate · PAR30 | 2,069,175.39 · 20.5008 % |
| DPD buckets (loans) | 0 = 25,098 · 1–30 = 947 · 31–60 = 292 · 61–90 = 125 · 90+ = 1,493 |

Full project: 26 models, 1 seed, 195 tests → 221 pass, 1 warn (known A4 residue). The four
FIFO business tests pass with 0 rows. FPD30 denominator (24,821) equals the independent pandas
anchor from 2026-09-26.

**Hand check:** a payment of 122,800 on 2026-03-22 is split 61,400 / 61,400 across installments
1 and 2 of its loan; another loan's payment of 2026-05-12 settles installments 4 and 5 at once
while installment 6 (due 2026-07-16) stays unpaid and *not* overdue. Both behaviours are the
README's "one payment may settle several installments".

**Finding / decision:**
- The plan is paid unusually punctually: median days-to-settle is 0 and 46,386 installments
  were paid early. Delinquency is concentrated: 1,493 loans sit in the 90+ bucket and drive
  PAR30; FPD30 flags are mostly *late payers* (1,657) rather than never-payers (547).
- Zero unallocated excess confirms that customers never pay beyond the plan total, so
  "outstanding" in A11 is never negative and no refund logic is needed.
- Only 2 installments are touched by the single post-snapshot payment, so the as-of cut (A20)
  matters conceptually more than numerically here.

**DMBOK dimension:** accuracy (money conservation tests), consistency (FIFO order, paid vs
received reconciliation), timeliness (settlement dates, as-of), integrity (loan and payment
links).

**Commit:** `04c92bb` feat(silver): add FIFO payment allocation and fct_installment_status with
conservation tests

---

## Step 15 — Gold: dm_loan_delinquency_snapshot  (2026-09-27)

**Goal:** the first consumption model (README 4.1 gold 2): per valid loan as of 2026-06-30,
outstanding balance in USD, DPD and delinquency bucket, with PAR30 derivable in one line.

**Files:** `models/gold/dm_loan_delinquency_snapshot.sql`, `models/gold/gold.yml`, singular
tests `assert_snapshot_covers_every_valid_loan`, `assert_snapshot_dpd_matches_installments`,
`analyses/profiling/dq_17_delinquency_snapshot.sql`. Fix in
`fct_installment_status.is_overdue` (+ tests) and assumptions A24.

**Design:** the mart aggregates `fct_installment_status` per loan and classifies. It never
re-implements FIFO or as-of logic. Two secondary balances travel with the primary one so the
open definitions are visible: net of partial payments (A11 alternative) and valued at the
disbursement-date rate (A12 alternative).

**Command(s):**
```powershell
dbt build
dbt compile --select dq_16_fifo_and_delinquency dq_17_delinquency_snapshot
python scripts/run_analyses.py --pattern "dq_16*" --out evidence/fifo_and_delinquency.md --title "FIFO allocation and installment status as of the snapshot"
python scripts/run_analyses.py --pattern "dq_17*" --out evidence/delinquency_snapshot.md --title "Delinquency snapshot as of 2026-06-30 - PAR30 and sensitivity"
```

**Incident:** the first build failed the gold consistency test `(dpd > 0) = (n_overdue > 0)`
with 164 loans. Each had a single unpaid installment due exactly on the snapshot date:
`is_overdue` had been written with `<=` while DPD counts days *after* the due date. Fixed by
defining overdue as strictly past due (A24) and adding `is_overdue ⇒ days_past_due > 0` to the
installment fact. Logged as AI error 3.7. Effect: overdue installments 6,120 → 5,935 and overdue
amount 483,904.28 → 468,613.91 USD; PAR30, FPD30, buckets and statuses unchanged.

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| Loans in snapshot | 27,955 (every valid loan, settled ones included) |
| Status | SETTLED 18,890 · CURRENT 6,208 · DELINQUENT 2,857 |
| DPD buckets (loans / USD share) | 0: 25,098 / 68.84 % · 1–30: 947 / 10.66 % · 31–60: 292 / 2.95 % · 61–90: 125 / 1.25 % · 90+: 1,493 / 16.29 % |
| **Total outstanding balance (Q5)** | **2,069,175.39 USD** at 2026-06-30 rates (COP 4,141.00 · BRL 5.6113) |
| **PAR30 (Q5)** | 424,197.74 / 2,069,175.39 = **20.5008 %** (1,910 loans with DPD > 30 of 9,065 with balance) |
| PAR30 by currency | COP 19.79 % · BRL 21.67 % |
| Sensitivity A11 (net of partial) | 2,057,634.75 USD · PAR30 20.5683 % |
| Sensitivity A12 (disbursement-date rates) | 2,047,237.02 USD · PAR30 20.4910 % |
| PAR30 by disbursement year | 2025: 77.88 % · 2026: 6.43 % |
| Delinquent loans that never paid | 735 |
| Top merchant by outstanding | 1607 with 22.47 % of the balance |

Full project: 27 models, 1 seed, 218 tests → 245 pass, 1 warn (known A4 residue). The warehouse
now has the four intended schemas: bronze (7), silver (20), gold (1), dq_audit.

**Finding / decision:**
- The two open definitions move PAR30 by less than 0.1 pp and the balance by about 1 %, so the
  README-literal choices (A11 gross, A12 snapshot rate) are safe and documented with their
  sensitivities rather than argued about.
- PAR30 is a 2025-vintage problem: 77.88 % of the outstanding balance of 2025 loans is more than
  30 days late, against 6.43 % for 2026. The old book is what remains unpaid; the young book is
  mostly not yet due. This matters for Q6's "concentration risk in your own metrics".

**DMBOK dimension:** consistency (bucket/status/DPD invariants), accuracy (gold recomputed from
silver), completeness (every valid loan present).

**Commit:** `c487dd6` feat(gold): add loan delinquency snapshot with PAR30 sensitivities; fix
overdue boundary (A24)

---

## Step 16 — Gold: agg_merchant_monthly and the month-end series  (2026-09-27)

**Goal:** the last required model (README 4.1 gold 1): merchant × month with applications,
approval rate, GMV in USD, disbursed loans, FPD30 and PAR30, under the category in effect at
the time. Decide A13 (how PAR30 is measured per month) and A25 (which category names a month).

**Files:** `models/silver/intermediate/int_loan_month_end_status.sql` (+ `intermediate.yml`),
`models/gold/agg_merchant_monthly.sql` (+ `gold.yml`), singular tests
`assert_month_end_series_matches_snapshot`, `assert_agg_merchant_monthly_reconciles`,
`analyses/profiling/dq_18_merchant_monthly.sql`.

**Design:**
- **A13, PAR30 as a stock.** A new intermediate states every valid loan at every month end from
  its disbursement month to the snapshot month, using `settled_date_any` (FIFO settlement dates
  do not depend on the reporting date, so no re-allocation). The aggregate takes the merchant's
  outstanding and PAR30 balance at each month end from it. FPD30 stays a cohort metric by
  disbursement month. A cohort view of PAR30 as of the snapshot is kept as
  `par30_cohort_rate_at_snapshot`.
- **A25, category at month end.** Grain merchant × month means one category per row; the
  SCD2 version in effect on the last day of the month is used, and rows where the category
  changed inside the month are flagged with the earlier category.
- **Dense grid.** Every merchant × month from 2024-12 to 2026-06 in which the merchant existed:
  13,299 rows, 11,327 with activity, so monthly series have no gaps. Rates are NULL when the
  denominator is 0.

**Command(s):**
```powershell
dbt build
dbt compile --select dq_18_merchant_monthly
python scripts/run_analyses.py --pattern "dq_18*" --out evidence/merchant_monthly.md --title "agg_merchant_monthly - reconciliation and merchant concentration (Q6)"
```

**Incident:** `category_changed_in_month` first flagged 171 rows against 157 known category
changes. The extra 14 were merchants whose first version starts inside the month
(NULL at month start compared with `is distinct from`). Fixed to require a non-NULL earlier
category; 153 rows remain flagged, the 4 missing changes being effective on the 1st of a month,
which is correctly "not inside the month".

**Result (validated from a clean `target` in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| `int_loan_month_end_status` | 264,143 loan-months (125,521 with a balance) |
| `agg_merchant_monthly` | 13,299 rows · 700 merchants · 19 months (2024-12 … 2026-06) · 153 category changes inside a month · 209 rows under UNKNOWN |
| Reconciliation Q1 from the aggregate | 59,059 / 33,007 / 55.8882 % |
| Reconciliation Q2 · Q3 | 27,955 / 8,780,942.16 USD · 1,540 / 473,272.15 USD |
| Reconciliation Q4 · Q5 | 8.8796 % / 7.7922 % · 2,069,175.39 USD / 20.5008 % |
| Month-end series at 2026-06-30 vs snapshot | identical loan by loan (singular test, 0 rows) |
| Portfolio PAR30 by month end | 0.0 % (2025-01) rising every month to 20.5 % (2026-06) |
| Portfolio FPD30 by cohort | stable band 7.8 %–9.6 % across 16 cohorts |
| **Q6 top 5 by GMV** | 1607 BR 23.49 % · 1397 CO 7.78 % · 1664 CO 4.32 % · 1030 CO 2.36 % · 1286 CO 1.69 % = 39.63 % |
| Q6 concentration | top 20 = 53.86 %; 15 merchants make 50 % of GMV, 141 make 80 %; BR = 40.02 % of GMV |
| Q6 risk of the top 5 vs the rest | FPD30 9.20 % vs 8.67 % · PAR30 20.53 % vs 20.48 % |
| Q6 portfolio without merchant 1607 | FPD30 8.6432 % (vs 8.8796 %) · PAR30 20.2075 % (vs 20.5008 %) |

Full project: 29 models, 1 seed, 244 tests → 273 pass, 1 warn (known A4 residue).

**Finding / decision:**
- **Every business question is now reproducible from gold alone**, and the reconciliation test
  ties the aggregate back to the facts on eight totals. This is the "layer that settles the
  argument" the README asks for: Risk and Merchant teams read the same numbers.
- **PAR30 climbs monotonically because nothing is ever written off:** loans in the 90+ bucket
  stay in the denominator and numerator forever, so a young, growing book shows a rising PAR30
  by construction. That is an interpretation to state in RESULTS Q5/Q6, not a data error.
- **Concentration:** one Brazilian education merchant is 23.49 % of GMV and 22.47 % of the
  outstanding balance; removing it moves FPD30 by 0.24 pp and PAR30 by 0.29 pp. The portfolio
  metrics are not hostage to it today, but a change in its book (or its category, since it has
  a single SCD2 version) would move every headline number. The month-end vs cohort PAR30 for
  1607 (21.51 % vs 0.0 % for the 2026-06 cohort) shows why A13 matters: the cohort view of a
  fresh month says nothing about the merchant's risk.

**DMBOK dimension:** consistency (series vs snapshot, aggregate vs facts), accuracy (rates
bounded, numerators ≤ denominators), integrity (SCD2 version per month), completeness (dense
grid).

**Commit:** `699b3b0` feat(gold): add agg_merchant_monthly with month-end PAR30 series,
category-at-month-end and reconciliation tests

---

## Step 17 — Documentation, exposures, DMBOK matrix and dbt artifacts  (2026-09-27)

**Goal:** close README 4.4 (documentation of the gold models and of every non-trivial column,
grain in every description) and produce the artefacts a reviewer needs to verify the run
without re-executing it.

**Files:** `models/gold/gold.yml` (every column of both gold models documented; two exposures,
README 4.5), `scripts/build_data_quality_matrix.py` → `DATA_QUALITY.md`,
`evidence/dbt_artifacts/{manifest,catalog,run_results}.json`, `evidence/dbt_build.log`.

**Command(s):**
```powershell
dbt build --no-use-colors 2>&1 | Out-File -Encoding utf8 evidence/dbt_build.log
python scripts/build_data_quality_matrix.py
dbt docs generate
New-Item -ItemType Directory -Force evidence/dbt_artifacts | Out-Null
Copy-Item target/run_results.json, target/manifest.json, target/catalog.json evidence/dbt_artifacts/
```

**Incident:** the first parse of the documented `gold.yml` failed with a YAML syntax error:
five column descriptions contained `: ` inside a plain scalar ("Secondary view: …"), which
YAML reads as a nested mapping. Quoted. A side effect was instructive: the failed build left an
empty `run_results.json`, so the matrix generator reported every test as "not run" until the
project was rebuilt. The generator now normalises severities and the run timestamp it prints
makes a stale artefact visible.

**Result (validated in a scratch copy, then reproduced here):**

| Measure | Value |
|---|---|
| Parse | 29 models, 18 analyses, 244 tests, 1 seed, 7 sources, **2 exposures**, no deprecations |
| Build | 273 pass, 1 warn (known A4 residue), 2 NO-OP (exposures) |
| `DATA_QUALITY.md` | 244 tests: completeness 70 · validity 64 · consistency 35 · uniqueness 27 · integrity 24 · accuracy 14 · timeliness 10; 30 of 30 models and seeds covered; 0 tests without a dimension |
| Artefacts | manifest 2.0 MB · catalog 0.5 MB · run_results 0.4 MB (292 entries) |

**Decision:** `DATA_QUALITY.md` is generated, never edited by hand: it reads
`config.meta.dq_dimension` from the manifest and the status from the run results, so adding or
changing a test changes the matrix on the next run. The exposures name the two consumers the
README describes (Risk review, Merchant report) and make the "same numbers for both teams"
statement visible in the lineage graph.

**DMBOK dimension:** all seven, as the matrix.

**Commit:** *(filled after commit)*
