# Worklog — AI Challenge (contact triage)

Step-by-step trace of how the solution was built. One entry per step; each entry maps to a
commit. The plan these steps follow is in `IMPLEMENTATION_PLAN.md`. Same format as the data
challenge worklog.

---

## Step 00 — Analysis, profiling and plan  (2026-09-27)

**Goal:** understand the challenge and the data before writing code; record the decisions.

**Command(s):** profiling of `data/messages.jsonl` with a pandas/regex script (channels,
timestamp shapes, duplicates and near-duplicates, sensitive-data patterns, multi-intent, risk
signals, taxonomy gaps, rough keyword bucketing); Anthropic API reference loaded for model ids,
pricing, structured outputs and prompt caching; credential check on the machine (none present).

**Result:** findings in `IMPLEMENTATION_PLAN.md` §4 (regenerated as evidence in step 1).
Four decisions taken with the author (plan §3): personal key now and Addi's key when it arrives,
Claude Opus 5 with a measured Haiku 4.5 comparison, pytest + eval harness per Anthropic's guide,
human-confirmed gold set of 80–100 messages.

**Finding / decision:** an early observation of mojibake in one message was a console-rendering
artefact; the file has zero such characters. Corrected in the plan.

**Credential check (D1):** a personal key was placed in `deliverables/.env`; verified that the
file is git-ignored and untracked, that the value has the expected shape (never printed), and
that it authenticates: `models.retrieve("claude-opus-5")` OK and a 16-token
`messages.create` on `claude-opus-5` returned `end_turn` (19 input / 4 output tokens). The key
requested from Addi will replace it in the same file when it arrives.

**Environment:** Python 3.13 venv in `deliverables/.venv`; `anthropic 1.8.0`, `pydantic 2.13.5`,
`python-dotenv 1.2.3` installed during the check; the rest of the dependencies in step 0.

**Commit:** `70d6e9e` docs(ai): add implementation plan, decision log, worklog and HOW_I_WORKED
skeleton

---

## Step 01 — Profiling evidence, taxonomy v2, routing policy, output schema  (2026-09-27)

**Goal:** turn the analysis into data the pipeline consumes: the taxonomy as YAML (with KB
section ids), the routing policy as YAML, the output contract as pydantic models, and a test
suite that keeps the four consistent. Plus the profiling as committed evidence.

**Files:** `scripts/profile_messages.py` → `evidence/message_profiling.md`;
`lumo_triage/policy/taxonomy.yaml`, `lumo_triage/policy/routing.yaml`, `lumo_triage/schema.py`,
`TAXONOMY.md`, `tests/test_policy_consistency.py`; `requirements.txt` (top-level pins) and
`requirements-lock-py313.txt`.

**Command(s):**
```powershell
python scripts/profile_messages.py
python -m pytest tests/test_policy_consistency.py -q
```

**Result (validated in the working copy, then reproduced by the author):**

| Artefact | Content |
|---|---|
| `evidence/message_profiling.md` | 340 messages: channels 119/115/106, two timestamp shapes, 3 exact and 55 near-duplicate messages, 23 regex signals with counts, rough bucketing over 20 buckets with 28 unmatched |
| `taxonomy.yaml` | 25 reasons (17 original + 8 added), 17 KB section ids bound to the exact markdown headings, 9 flags, 5 priorities with SLAs, example message ids per reason |
| `routing.yaml` | 4 actions, 10 queues, 7 ordered overrides, 3 priority bumps, verifier rules, 4 Spanish templates |
| `schema.py` | `Classification` (what the model returns) and `TriageRecord` / `BatchSummary` (what the pipeline writes); reason enum generated from the YAML |
| `tests/test_policy_consistency.py` | 9 tests: unique ids, enum = YAML, valid defaults, no model drafts without policy, KB headings exist, cited sections exist, overrides reference known values, example ids exist and are not reused, templates are Spanish and short |

**Incident:** the first test run failed at YAML parse time: three plain scalars in
`taxonomy.yaml` were ambiguous (a `: ` inside a note, a value starting with a double quote,
and comma-separated descriptions inside flow mappings, which YAML splits into extra keys).
The same class of error as the data challenge's `gold.yml`; the consistency tests now load
both files, so it cannot reach the pipeline unnoticed. Logged in `HOW_I_WORKED.md` §3.2.

**Key decisions:**
- The taxonomy is data, not prose: the prompt, the routing and the tests read the same YAML,
  so a reason cannot exist in one place and not the others.
- `policy_coverage` is a property of the reason, and reasons with `none` can never receive a
  model-written draft (enforced by a test). "The policy doesn't cover it" becomes a routing
  outcome with the gap named.
- Priority is computed by code from reason and flags; the model never sets it.

**Commit:** `9b886da` feat(ai): add taxonomy v2, routing policy, output schema, consistency
tests and message profiling evidence

---

## Step 02 — Deterministic layer  (2026-09-27)

**Goal:** everything that does not need a model, as tested code: normalisation, exact and
near deduplication, verbatim entity extraction, tier-0 rules for content-free messages and
high-precision flag detectors.

**Files:** `lumo_triage/normalize.py`, `lumo_triage/extract.py`, `lumo_triage/rules.py`,
`tests/test_deterministic.py` (69 tests); `scripts/profile_messages.py` normaliser fixed;
`requirements.txt` and the lock without `rapidfuzz`.

**Command(s):**
```powershell
python -m pytest
python scripts/profile_messages.py
```

**Result:** 78 tests pass (9 policy + 69 deterministic), all on real messages plus adversarial
fixtures; 14 messages resolved by tier-0 without a model call; 2 exact-duplicate pairs and 55
near-duplicate messages, identical in code and evidence.

**Incidents (four, all caught by the tests):**
1. `rapidfuzz.distance.Jaccard` does not exist in the installed RapidFuzz 3.14.6; the assistant
   wrote it from memory. Replaced by a pure-Python Jaccard with union-find (the same definition
   as the evidence) and `rapidfuzz` removed from the dependencies. HOW_I_WORKED 3.3.
2. The document regex captured a trailing period (`9000000003.`); the pattern now must end on a
   digit.
3. Punctuation-only messages (`...`, `?????`) hashed to the same empty content and were linked
   as duplicates; messages without tokens are now excluded from exact deduplication, in code
   and in the profiling script.
4. The profiling script's normaliser left double spaces where punctuation had been, hiding one
   real duplicate pair ("este mes no voy a poder pagar…", MSG-155 / MSG-207) and reporting
   3 duplicates instead of 2. Fixed to the same canonical form as the code; the figure in the
   plan was corrected. HOW_I_WORKED 3.4.

**Key decisions:**
- Naive timestamps are Bogotá local time (40 of 340), converted to UTC; documented in the
  module and in DESIGN.md.
- Entities are verified verbatim against the normalised text, ours and later the model's; a
  masked identifier is never completed; the model may fill empty fields but never overwrite
  a rule-extracted one.
- Tier-0 is deliberately narrow: MSG-346 ("ggg asdkjf no se q paso aqui jajaja") mixes gibberish
  with words and is left to the model rather than force-closed by a rule.
- Flag detectors are high-precision patterns; the model can add flags, the routing trusts both.

**Commit:** *(filled after commit)*
