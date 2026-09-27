# AI Log — Data Challenge

> Required deliverable (README section 6). Filled in as the work happens, not reconstructed at
> the end. Tool used: Claude Code (Anthropic) inside VS Code.

---

## 1. What I delegated and what I didn't

| Delegated to the AI assistant | Kept for myself | Why |
|---|---|---|
| Exploratory profiling scripts over the raw CSVs | Deciding which anomalies are real business rules vs noise | The AI finds patterns fast; judging their business meaning is my responsibility |
| First drafts of SQL models, macros and YAML | Reviewing and approving every model line by line before it runs | I must be able to explain and defend every line |
| *(to be completed as work progresses)* | | |

---

## 2. Key prompts (3–5 decisive ones)

*(to be completed; only prompts that changed the direction of the work)*

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

### 3.5 *(to be completed)*

---

## 4. How I verified the final numbers in `RESULTS.md`

*(to be completed in Phase 5: independent pandas cross-check, reconciliation of every
difference, row-count lineage from bronze to gold)*
