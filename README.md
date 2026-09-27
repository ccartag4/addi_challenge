# AI Solutions — Technical Assessment (Lumo)

Submission for the two challenges described in `AI_amplifier_Technical_Assessment.md`.

| Challenge | Folder | Status | Start here |
|---|---|---|---|
| Data challenge — lending warehouse (dbt on DuckDB) | `data_challenge/deliverables/` | complete | [`README.md`](data_challenge/deliverables/README.md) → run in three commands · [`RESULTS.md`](data_challenge/deliverables/RESULTS.md) → the seven answers · [`ARCHITECTURE.md`](data_challenge/deliverables/ARCHITECTURE.md) → diagrams and requirement map |
| AI challenge — contact triage and reply drafting | `ai_challenge_contact_triage/deliverables/` | in progress | — |

The original challenge materials (data, READMEs, taxonomy, knowledge base) are unchanged; all
work lives under each challenge's `deliverables/` folder, as requested.

## Data challenge in one screen

- **What:** Bronze → Silver → Gold dbt project over the seven raw extracts: 29 models, 1 seed,
  244 tests (16 business tests), 2 exposures. `dbt build` → 273 pass, 1 expected warn.
- **Answers:** 59,059 valid applications and 55.89 % approval; 27,955 loans and 8,780,942.16 USD
  GMV; 2026-01 cohort 1,540 loans / 473,272.15 USD; FPD30 8.88 % (7.79 % for 2026-01);
  PAR30 20.50 % on 2,069,175.39 USD outstanding at 2026-06-30; top merchant 23.49 % of GMV, top
  five 39.63 %; 29,093 real people behind 30,000 customer ids.
- **Verification:** every figure recomputed independently from the raw CSVs with pandas (24 of
  24 checks, loan by loan) and reproducible from a fresh clone.
- **Write-ups:** `AI_LOG.md` (how the AI assistant was used, seven cases where it was wrong,
  how the numbers were verified), `ASSUMPTIONS.md` (A1–A25 definitions, F1–F18 findings),
  `DATA_JOURNEY.md` (row-by-row accounting), `DATA_QUALITY.md` (generated DMBOK matrix),
  `WORKLOG.md` and `IMPLEMENTATION_PLAN.md` (the build trace).
