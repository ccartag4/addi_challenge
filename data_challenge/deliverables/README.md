# Lumo lending warehouse — dbt on DuckDB

Bronze → Silver → Gold model over Lumo's lending extracts (`../data/`), built with dbt-core
1.12 and DuckDB. Answers to the seven business questions are in **`RESULTS.md`**; every number
there is reproducible with the commands below and verifiable without running anything from the
files under `evidence/`.

## Run it in three commands

From this folder (`data_challenge/deliverables/`), with Python 3.11–3.13 available:

```bash
pip install -r requirements.txt      # 1. dbt-core, dbt-duckdb, duckdb, pandas (pinned)
dbt deps                             # 2. dbt_utils
dbt build                            # 3. seeds + 29 models + 244 tests → lumo.duckdb
```

Expected: `PASS=273 WARN=1 ERROR=0 SKIP=0 NO-OP=2`. The single warning is deliberate: 3 valid
applications whose every CDC event carries the placeholder customer id (finding F4, assumption
A4). The two NO-OPs are exposures.

Use a virtual environment if you prefer (`python -m venv .venv` then activate it). The
connection profile (`profiles.yml`) lives in this folder and creates the local file
`lumo.duckdb` (about 60 MB); no configuration is needed. On Windows, run from PowerShell or
cmd. A `RequestsDependencyWarning` about `chardet` may be printed by a transitive dependency;
it is harmless. Verified end to end on a fresh clone (see `WORKLOG.md`, step 19).

## Then, optionally

```bash
dbt compile --select "path:analyses/results"
python scripts/run_analyses.py --pattern "q0*" --out evidence/results.md   # the 7 answers as tables
python scripts/crosscheck_pandas.py            # recompute everything from the raw CSVs, compare (24 checks)
python scripts/build_data_quality_matrix.py    # regenerate DATA_QUALITY.md from the run
dbt docs generate && dbt docs serve            # lineage, column docs, exposures
```

To move the snapshot date: `dbt build --vars '{snapshot_date: "2026-03-31"}'`. Every as-of
column, FPD30, PAR30 and the month-end series follow the variable.

## What is where

```
models/
  bronze/                 7 views: 1:1 reads of the CSVs, every column as text
  silver/staging/         7 views: typed, parsed (3 timestamp shapes), deduplicated
  silver/intermediate/    CDC ranks, FX daily calendar (forward fill), loan validation,
                          payment classification (reversals), FIFO allocation, month-end series
  silver/core/            dim_customer (person grain) + bridge, dim_merchant (SCD2),
                          fct_application, fct_loan, fct_payment, fct_installment_status
  gold/                   dm_loan_delinquency_snapshot, agg_merchant_monthly (+ 2 exposures)
macros/                   parse_utc_ts, business time (Bogotá), text helpers, schema naming
tests/                    16 singular business tests (reconciliations, FIFO conservation, SCD2)
seeds/                    canonical city names
analyses/profiling/       dq_01 … dq_18: the profiling and verification queries, in build order
analyses/results/         q01 … q07: the official result queries
scripts/                  Markdown export, DMBOK matrix generator, independent pandas cross-check
evidence/                 outputs of all of the above + dbt artefacts + build log
```

| Document | Purpose |
|---|---|
| `RESULTS.md` | the seven answers, with the model/query behind each and the interpretation |
| `ASSUMPTIONS.md` | A1–A25 definitions and F1–F18 data quality findings |
| `DATA_JOURNEY.md` | row-count funnel with the reason for every delta, step ledger, error ledger |
| `DATA_QUALITY.md` | generated DMBOK matrix of the 244 tests |
| `AI_LOG.md` | how the AI assistant was used, where it was wrong, how the numbers were verified |
| `WORKLOG.md`, `IMPLEMENTATION_PLAN.md` | the build trace and the plan it followed |

## Conventions

- Every model description starts with its grain. Every test declares `config.meta.dq_dimension`
  (DAMA-DMBOK), which is what `DATA_QUALITY.md` is generated from.
- Business dates are UTC timestamps converted to `America/Bogota`; amounts in USD use the
  forward-filled daily FX calendar; all parameters (`snapshot_date`, `cutover_date`,
  `business_tz`, `placeholder_customer_id`, `raw_data_path`) are project vars, never literals.
- Failed test rows are stored in the `dq_audit` schema of `lumo.duckdb` (`store_failures`).

Tested on Windows 11 with Python 3.13.13, dbt-core 1.12.5, dbt-duckdb 1.11.0, duckdb 1.5.5.
