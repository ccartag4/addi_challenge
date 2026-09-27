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
*(second commit hash filled after run)*

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

**Commit:** *(filled after commit)*
