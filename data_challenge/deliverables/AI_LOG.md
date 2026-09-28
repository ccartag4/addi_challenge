# AI Log — Data Challenge

> Required deliverable (README section 6). Filled in as the work happens, not reconstructed at
> the end. Tool used: Claude Code (Anthropic) inside VS Code.

---

## 1. What I delegated and what I didn't

The working rule for the whole challenge: **the assistant produces candidates, I decide and
verify, and I run every command myself.** Nothing reached the repository without me reading it
and the output of running it.

| Delegated to the AI assistant | Kept for myself | Why |
|---|---|---|
| Exploratory profiling scripts (pandas, then SQL analyses `dq_01`–`dq_18`) | Deciding which anomaly is a business rule (placeholder customer, legacy ×100, reversals) and which is noise; naming and numbering every finding | The assistant finds patterns fast; deciding what they *mean* for Lumo's numbers is the job |
| First drafts of every model, macro, test and YAML block | Approving each file line by line before it ran; rejecting or changing what I could not explain | The assessment's one hard rule: defend every part of what I submit |
| Boilerplate: project config, `.gitignore`, export scripts, the DMBOK matrix generator, the cross-check script | Choosing the engine (DuckDB), repository location, layer layout, commit granularity, what goes in `evidence/` | Reproducibility choices shape how the reviewer verifies the work |
| Proposing options for the open definitions (A11, A12, A13, A25) with pros and cons | Choosing the primary definition and requiring the alternative to be published next to it | The README leaves them open on purpose; the choice must be mine and visible |
| Drafting the write-ups from the worklog | Deciding severity of each test (warn vs error), which residues to keep with a flag rather than drop, and the interpretation in Q5/Q6 | These are judgement calls about the business, not text |
| Running validations in a scratch copy before handing me commands | Running the real build, reading every `dbt` log line for `Deprecat` and `FAIL`, and pasting outputs back | The assistant's scratch check passed for the wrong reason once (3.4); my run is the one that counts |

What I did **not** delegate at all: the four decisions in `IMPLEMENTATION_PLAN.md` §3, the
answers to the interview-style questions I asked myself after profiling (why 100 and not 1,000,
why exclude reversals rather than net them, why the ghost customer is a placeholder), and the
final reading of every evidence file before each commit.

---

## 2. Key prompts (the ones that changed the direction of the work)

1. **"Analyze and understand the challenge and give me an idea of how to approach the solution"**
   (before any code). Instead of an architecture sketch, this produced a profiling pass over the
   raw CSVs and a list of planted traps with figures: three timestamp shapes, epoch
   milliseconds, FX gaps, legacy ×100, reversals, deleted applications, redundant customer ids.
   It set the anchors that every later layer was checked against, and it made "profile first,
   model second" the order of the whole build.

2. **"I want to do it myself with commands so I understand the detail, you explain; leave a
   step-by-step record; add DAMA-DMBOK for quality documentation; ask me if you have doubts."**
   This prompt shaped the method more than any technical one: one worklog entry and one commit
   per step, every test tagged with a DMBOK dimension (which later became a generated matrix),
   validations in a scratch copy before I ran anything, and four explicit decision questions
   (engine, repository, DMBOK depth, language) answered and recorded before step 0.

3. **"Add the implementation plan as an additional document, as evidence, with the questions you
   asked me and my answers."** It turned the plan from chat into a committed decision log, and
   from then on every deviation from it (uv → venv, the month-end series, the extra documents)
   was written down as a deviation instead of silently absorbed.

4. **"Is there a way to create a document that says exactly which data it is and why it errored
   or was done in a certain way? A table explaining what happened at each step."** This produced
   `DATA_JOURNEY.md` and the funnel analysis `dq_15`. Its lasting effect was a discipline: no row
   may disappear between layers without a finding or assumption number attached, and every
   error, including the assistant's, has a root cause on record.

5. **The recurring "me sale esto" with a pasted output.** Not one prompt but the loop that caught
   most problems: the failed `dq_*` selector (3.4), the deprecation summaries (3.3, 3.5), the
   `.user.yml` in a commit (3.2). Pasting the raw output rather than describing it is what let
   the assistant see what it had assumed.

---

## 3. Cases where the AI got it wrong

### 3.1 Epoch-millisecond timestamps treated as unparseable

- **What it produced:** the first profiling pass parsed timestamps with a generic parser.
  It reported 6,399 application events and 1,440 loans with unparseable dates, and 1,440 loans
  "outside the FX rate range".
- **How I caught it:** the unparseable count in loans (1,440) was exactly equal to the
  "outside FX range" count. Two unrelated checks should not coincide that precisely, so the
  second was a side effect of the first. Inspecting the raw values showed 13-digit numbers such
  as `1778106658000`: Unix epoch in milliseconds.
- **What I did:** added an explicit epoch branch to the parser. After the fix, unparseable
  timestamps dropped to 0 in all four files and the "outside FX range" loans disappeared.
  The final solution uses a dedicated `parse_utc_ts` macro that handles the three formats.

### 3.2 Incomplete `.gitignore`: dbt's `.user.yml` committed

- **What it produced:** the `.gitignore` drafted by the AI covered `target/`, `dbt_packages/`,
  `logs/` and `*.duckdb`, but not `.user.yml`. It also predicted the commit would contain seven
  files, without checking what dbt writes on its first run.
- **How I caught it:** the commit output listed `create mode … .user.yml`, a file nobody had
  written. Inspecting it showed a single line, `id: <uuid>`: dbt's anonymous telemetry
  identifier, specific to this machine.
- **What I did:** added `.user.yml` to `.gitignore`, removed it from the index with
  `git rm --cached`, and disabled telemetry in `dbt_project.yml`
  (`flags: send_anonymous_usage_stats: false`), which is also the appropriate default when a
  project handles customer data.
- **Lesson:** verify tool side effects with `git status --short --ignored` before trusting a
  predicted file list.

### 3.3 Deprecated dbt syntax for test metadata

- **What it produced:** every bronze test was written with `meta:` as a direct property of the
  test (`- not_null: {meta: {...}}`), the syntax valid up to dbt 1.9.
- **How I caught it:** the first `dbt run` printed a deprecation summary with exactly 10
  occurrences of `PropertyMovedToConfigDeprecation`, the same number as tests. Running
  `dbt parse --no-partial-parse --show-all-deprecations` gave the exact message: `meta` must be
  moved into `config`.
- **What I did:** rewrote the ten tests as `config: {meta: {...}}` and re-parsed until the
  warning count was zero. Adopted that form as the convention for every later layer.
- **Lesson:** the assistant's knowledge of a tool lags its latest release. A version pinned in
  `requirements.txt` plus reading the tool's own warnings is the check, not the assistant's
  memory.

### 3.4 A validation that passed for the wrong reason

- **What it produced:** the instruction `dbt compile --select "dq_*"` to compile the profiling
  analyses, reported as validated in a scratch copy of the project.
- **How I caught it:** in my environment dbt answered "The selection criterion 'dq_*' does not
  match any enabled nodes" and the export script found nothing to run. The assistant's scratch
  check had passed only because previous `dbt show --select <analysis>` calls had already left
  compiled SQL under `target/compiled/`, so the script read stale files.
- **What I did:** tested the selector variants with `dbt ls`. Name wildcards do not select
  analyses; `path:analyses/profiling` and `resource_type:analysis` do. Fixed the command in the
  worklog and in the script's usage notes.
- **Lesson:** a validation must start from a clean state, or it validates the leftovers of the
  previous attempt. Same rule as for the FIFO and the FX fill later: re-run from scratch before
  trusting a green result.

### 3.5 Second deprecated syntax: test arguments outside `arguments:`

- **What it produced:** the 27 staging tests that take parameters (`accepted_values`,
  `dbt_utils.accepted_range`, `expression_is_true`, `unique_combination_of_columns`) were
  written with their parameters as top-level keys, the pre-1.10 form.
- **How I caught it:** the first `dbt build` of the staging layer reported
  `MissingArgumentsPropertyInGenericTestDeprecation: 27 occurrences`. Everything passed, so
  without reading the warning summary the problem would have shipped.
- **What I did:** moved every parameter under `arguments:` and re-ran until the deprecation
  count was zero. Same root cause as 3.3 (assistant knowledge older than dbt 1.12.5); the
  fix for the process is to grep the log for `Deprecat` after every run, which is now part of
  the step checklist.

### 3.6 Profiling that counted values but not NULLs

- **What it produced:** the merchant profiling analysis (`dq_08`) summarised categories with a
  `string_agg` of distinct values and counts. The seven categories added up to 846 rows, but
  the extract has 862. Nobody, human or assistant, subtracted. The staging `accepted_values`
  test then passed because that test ignores NULLs by design.
- **How I caught it:** building `dim_merchant` with a `not_null` test on `category` failed
  with 16 rows. A second symptom was already visible in `dq_11`: 162 second versions, 157
  category changes and 0 "name-only" changes, which cannot all be true.
- **What I did:** inspected the 16 rows (11 single-version merchants never categorised, 5
  second versions whose first version had a category), added explicit NULL counts per column
  to `dq_08`, and defined A17: carry forward when an earlier version exists, `UNKNOWN`
  otherwise, with `category_source` and `category_imputation` columns so the fill is auditable.
  Measured the impact first: 574 valid applications and 265 loans sit on those versions, so
  dropping them was not an option.
- **Lesson:** a profiling query must always report NULL counts per column; distinct-value
  summaries and `accepted_values` tests both hide NULLs. Added as a standing item of the
  per-extract checklist.

### 3.7 "Overdue" defined with ≤ instead of <

- **What it produced:** `fct_installment_status.is_overdue = due_date <= as_of_date and not
  is_settled`, so an installment due exactly on the snapshot date and unpaid was flagged
  overdue while its `days_past_due` was 0.
- **How I caught it:** not by reading the SQL. The gold snapshot carries a consistency test,
  `(dpd > 0) = (n_overdue > 0)`, which failed with 164 loans: every one of them had a single
  unpaid installment due on 2026-06-30. Two definitions written by the same assistant in two
  models disagreed, and the cross-model test exposed it.
- **What I did:** made "overdue" strictly past the due date (A24), added the invariant
  `is_overdue ⇒ days_past_due > 0` to the installment fact, and re-ran dq_16 and dq_17 so the
  evidence matches the corrected definition. PAR30 and FPD30 do not move (both use > 30 days);
  only the count of "overdue installments" and the 1–30 bucket's loan count change.
- **Lesson:** boundary conditions (=, ≤, <) are where an assistant is most likely to be
  inconsistent with itself. Tests that relate two models' outputs catch what reading one model
  at a time does not.

### 3.8 A "reproducible" requirements file that only reproduced my machine

- **What it produced:** at step 03 the assistant recommended committing the full `pip freeze`
  as the reproducibility guarantee, and the README claimed Python 3.11–3.13. The fresh-clone
  test at step 19 passed, but it ran on the same OS and Python as the freeze.
- **How I caught it:** I asked for the requirements to be validated for Mac and Windows. The
  assistant checked wheel availability per platform with `pip download --platform` and then
  resolved the dependency tree per platform with `uv pip compile`. Two facts came out: the
  freeze pinned `networkx==3.7`, which requires Python 3.12+, so `pip install` fails on Python
  3.11 on any OS; and one dbt dependency (`dbt-core-experimental-parser`) is published as a
  pure-Python sdist only, which made the first binary-only check report a false failure on
  every platform until the package was inspected.
- **What I did:** split the file in two. `requirements.txt` now pins only the four top-level
  packages and lets pip resolve the transitive set for the reader's OS and Python (resolution
  verified for macOS arm64 and x86_64, Linux and Windows on 3.11, 3.12 and 3.13);
  `requirements-lock-py313.txt` keeps the exact tested environment, whose wheels were verified
  to exist for macOS and Linux on 3.13. The README states which combinations were executed and
  which were only resolved.
- **Lesson:** a freeze is a record of one machine, not a portability guarantee. "Works on a fresh
  clone" must be qualified by OS and Python version, and a claim about other platforms needs a
  check that targets those platforms.

---

## 4. How I verified the final numbers in `RESULTS.md`

Five layers, from cheapest to strongest. Every figure in `RESULTS.md` passed all five.

1. **Anchors before the pipeline existed.** On day one an exploratory pandas pass over the raw
   CSVs produced first estimates (valid applications, approved, GMV, cohort 2026-01, top
   merchants, people). They were written down before any dbt model was built, so the pipeline
   had numbers to be wrong against. GMV matched to the cent at step 12; the FPD30 denominator
   (24,821) matched at step 14.
2. **Row-count funnel with a reason for every delta.** `dq_15_row_count_funnel` (evidence in
   `evidence/row_count_funnel.md`, narrative in `DATA_JOURNEY.md` section A): 128,197 CDC rows
   → 60,000 applications → 59,059 valid; 28,075 loans → 27,955; 112,339 payment rows → 107,554
   effective; 30,000 customer ids → 29,093 people. No row disappears without a finding or
   assumption number attached.
3. **Contract tests between layers.** 244 tests, 19 of them singular business tests, run on
   every build. The ones that guard the published figures directly:
   `assert_payment_counts_reconcile` (A9 arithmetic), the four FIFO conservation tests
   (money in = money allocated, per payment, per installment, per loan, in FIFO order),
   `assert_snapshot_dpd_matches_installments` (gold recomputed from silver),
   `assert_month_end_series_matches_snapshot` (two computations of the same state agree loan by
   loan), and `assert_agg_merchant_monthly_reconciles` (the aggregate adds back to the facts on
   eight totals). `DATA_QUALITY.md` shows their status for the committed run.
4. **Definition sensitivity.** Where the README left a definition open I published the
   alternative next to the chosen figure instead of choosing silently: Q7 under
   document + country (29,439 / 561), Q5 net of partial payments (20.5683 %) and at
   disbursement-date rates (20.4910 %), Q3 under UTC months (1,541 loans). None of them changes
   the story; all of them are in `ASSUMPTIONS.md` with the reason for the primary choice.
5. **Independent recomputation from the raw files.** `scripts/crosscheck_pandas.py` rebuilds
   every answer from the CSVs with a different code path: its own timestamp parser, CDC resolved
   by sort-and-take-last, FIFO as an explicit per-loan loop in integer cents (the SQL uses an
   interval-overlap join in DECIMAL). It only touches the warehouse at the end, read-only, to
   compare. Result (`evidence/crosscheck_pandas.md`): 24 of 24 checks match, including DPD and
   outstanding balance on each of the 27,955 loans. The AI wrote this script too, so it is not
   "human vs AI"; it is "two implementations of the same written rules must agree", which is
   the check I can defend.

What I did **not** do: I did not compare against an external source of truth for FX or for the
business definitions, because none exists in the challenge. The published numbers are correct
*given ASSUMPTIONS.md*; each assumption is the thing to challenge.
