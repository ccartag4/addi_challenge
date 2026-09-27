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

**Reproduction note:** the commands of this challenge run from `ai_challenge_contact_triage/deliverables`
(venv, `pyproject.toml` and `scripts/` live there); running pytest from the repository root
fails to import `lumo_triage` because the ini file is not found.

**Commit:** `aa7cf85` feat(ai): add deterministic layer: normalisation, dedup, verbatim entity
extraction, tier-0 rules and flags with tests

---

## Step 03 — LLM classification  (2026-09-27)

**Goal:** the model decides *what the message is*, nothing else: structured output validated
against `Classification`, a cached system prompt rendered from the taxonomy YAML, retries and
failure handling in one place, every call traced, every response replayable offline.

**Files:** `lumo_triage/llm.py` (API wrapper: modes auto/live/offline, on-disk response cache,
JSONL trace, refusal / truncation / invalid-output handling, cost accounting),
`lumo_triage/classify.py` (system prompt from `taxonomy.yaml`, user turn with the text as data,
tier-0 and duplicate short-cuts, deterministic post-processing, small thread pool),
`lumo_triage/__main__.py` (`python -m lumo_triage classify`), `lumo_triage/schema.py`
(`Processing` gains served_by / effort / cache_write_tokens / llm_error; `classification`
becomes optional for the failure path), `lumo_triage/extract.py` (payment-date precision),
`tests/test_classifier.py` (23 tests on a fake SDK client), `tests/test_live_smoke.py`
(1 gated live test), `tests/test_deterministic.py` (+11 date cases), `pyproject.toml`
(`live` marker), `.env.example` (`LUMO_TRIAGE_EFFORT`).

**Before writing a single SDK call**, the request shape was checked in the installed package
(`anthropic 1.8.0`), not recalled: `fallbacks` accepts `"default"` (type alias in
`types/beta/beta_fallbacks_param.py`), `messages.parse()` is `create()` plus
`transform_schema()` plus client-side pydantic validation (`resources/beta/messages/messages.py`),
and `transform_schema` is exported at package level. HOW_I_WORKED 3.3 is the reason.

**Command(s):**
```powershell
python -m pytest -q                                                   # 110 passed, 1 skipped (live)
$env:LUMO_LIVE_TESTS = "1"; python -m pytest tests/test_live_smoke.py -q -m live
python -m lumo_triage classify --ids MSG-001,MSG-002,MSG-004,MSG-006,MSG-037,MSG-346 --workers 3
python -m lumo_triage classify --ids MSG-001,MSG-002,MSG-004,MSG-006,MSG-037,MSG-346 --workers 3   # replay
```

**Result (validated in the working copy):**

| Check | Evidence |
|---|---|
| Request accepted by the API with structured output, `fallbacks="default"`, cached system block, no sampling params | live smoke test passes: 3 messages, expected reasons, `stop_reason=end_turn` |
| Prompt cache works | every call after the first reads 7,426 cached prefix tokens; cache-read share 99 % of prompt tokens |
| Quality on 6 hand-picked messages | no_puede_pagar + vulnerable (MSG-001), saldo + secondary fecha_de_pago (MSG-002), cuenta_y_app with "5 intentos" correctly *not* repeat_contact (MSG-004), pago_anticipado (MSG-006), fuera_de_alcance/unrelated (MSG-037), ruido for the mixed gibberish (MSG-346) |
| Cost and latency | USD 0.078 for 6 messages (≈ 0.013 each: ~360 output tokens dominate), 5–6.5 s per call |
| Offline replay | second run: 0 live calls, 6 replays, USD 0.000 spent, identical output |
| Trace | `evidence/llm_calls.jsonl`: usage, cache tokens, latency, request id, served-by model per call; no message text |

**Full run (author, 340 messages, `python -m lumo_triage classify --workers 4`):**

| Item | Value |
|---|---|
| Decided without the model | 13 by tier-0 rules + 2 reused from exact duplicates |
| Model calls | 319 live + 6 replayed from the validation run; 0 unclassified; all served by `claude-opus-5` (no fallback) |
| Prompt tokens | 25,593 uncached / 2,383,746 read from cache / 29,704 written → 97.7 % served from cache |
| Output tokens | 118,691 (mean 365 per call: the JSON plus a little adaptive thinking) |
| Cost | USD 4.47 recorded, USD 4.39 spent by this run (≈ USD 0.014 per call) |
| Latency | p50 5.4 s, p95 7.3 s, max 16.5 s; about 10 minutes wall-clock with 4 workers |
| Confidence | 248 messages ≥ 0.90, 57 in 0.80–0.89, 13 in 0.70–0.79, 7 in 0.60–0.69, none below the 0.60 routing threshold |
| Distribution | all 25 reasons used; largest bucket 9.1 % (`pago_no_aplicado`); 80 messages (23.5 %) carry a secondary reason |
| Agreement with the taxonomy example ids | 176 of 182 (96.7 %); the 6 disagreements are two-intent messages where the expected reason came back as the secondary one |

The full breakdown is generated by `scripts/summarize_classifications.py` into
`evidence/classification_run.md` (distribution, flags, confidence bands with the low-confidence
messages listed, entity fill rates, post-processing codes, disagreements).

**Validation verdict:** no prompt change before the evaluation step. The seven messages under
0.70 are genuinely mixed ("no puedo pagar pero cuánto sería la mora…"), the disagreements are
defensible orderings of two requests, and a `classify-v2` prompt would invalidate the cache and
cost the run again for no measured gain. Two things carried into step 4: a secondary
`privacidad_habeas_data` (MSG-182, MSG-367, classified as `cancelacion` first) must still reach
the privacy owner, so routing has to look at secondary reasons with legal obligations, not only
at the primary; and `hablar_con_humano` as primary now appears 13 times with `requests_human`
on 6 more real topics, which is exactly the "human as flag" behaviour the policy expects.

**Incident:** reading the six outputs of the validation run showed `payment_date = "hoy"` on the
weather message (MSG-037). The model had left it null; the *rule* contributed it and the merge policy let the
rule win. Relative words now count as a payment date only next to a payment or due-date verb;
11 new cases pin the behaviour (MSG-011/213/385 keep theirs, MSG-037/125/150/178 lose a false
one). HOW_I_WORKED 3.5.

**Key decisions:**
- `create()` with `output_config.format` instead of `messages.parse()`: same schema, same
  validation, but the response object stays available on refusal or truncation, so usage and
  stop reason are always logged and the body can be cached for replay.
- Claude Opus 5 with default adaptive thinking and `effort=medium`; no `temperature` (rejected
  on this model): determinism for reviewers comes from the committed cache, not from sampling.
- The system prompt contains no sample text; boundary examples are synthetic, so the
  evaluation on the 340 messages is not contaminated.
- Code has the last word: entities merged (rules first) and re-verified verbatim, flags OR-ed,
  "human" demoted to a flag when another request exists, out-of-scope kind normalised, each
  adjustment leaving a `POST_*` code.
- A model failure (refusal after fallback, invalid output twice, API down, offline miss) still
  produces a record: `classification = null`, `LLM_FAILED`, routed to a person in step 4.
- Cost is reported twice: what the calls cost when made and what this run spent; a full replay
  shows the first and zero for the second.

**Commit:** *(filled after commit)*
