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

**Commit:** `5c981f5` feat(ai): add LLM classifier with structured output, prompt cache, offline
replay cache and call trace

---

## Step 04 — Routing, grounded drafting and the verifier  (2026-09-27)

**Goal:** code decides what to do with a classified message (priority, action, queue), the model
writes a Spanish reply only from the policy sections it is allowed to see, and code verifies
the reply before it can be marked sendable. One `TriageRecord` per message, end to end.

**Files:** `lumo_triage/kb.py` (sections by stable id from the four policy files),
`lumo_triage/routing.py` (overrides, defaults, priority arithmetic, reply source),
`lumo_triage/draft.py` (drafting prompt and `DraftOutput` schema), `lumo_triage/verify.py`
(eight checks), `lumo_triage/pipeline.py` (assembly, two-stage thread pools),
`lumo_triage/__main__.py` (`run` command), `policy/routing.yaml` (`OVR_HABEAS`, `reply_source`
condition, `extra_sections`, `reason_templates`, `template_citations`, `queue_labels_es`, more
forbidden phrases, `min_words`), `policy/taxonomy.yaml` (`policy_gap` per uncovered reason),
`schema.py` (`DraftReply.rejected_text`); tests `test_routing.py` (18), `test_draft_verifier.py`
(15), consistency tests extended. 148 tests, 1 skipped (live).

**Command(s):**
```powershell
python -m pytest -q
python -m lumo_triage run --ids MSG-001,MSG-002,MSG-003,MSG-004,MSG-005,MSG-006,MSG-008,MSG-009,MSG-010,MSG-013,MSG-016,MSG-018,MSG-026,MSG-036,MSG-037,MSG-182,MSG-269,MSG-291 --workers 3
```

**Result (author's validation, 18 messages chosen to cover every path):**

| Check | Evidence |
|---|---|
| Paths exercised | 8 `auto_reply`, 8 `auto_reply_and_route`, 2 `route_to_human`; 13 model drafts, 3 templates (fraud, greeting, off-topic), 2 no-reply |
| Verifier | 13 of 13 drafts passed all eight checks (citations inside the allowed set, every figure traceable to a cited section or to the customer's text, no forbidden promise, no document echo, length, Spanish, no placeholders, no stray contact details) |
| Grounding | every draft cites the sections it used; figures quoted exactly ("5 días calendario", "hasta 30 días calendario", "24 horas", "2 días hábiles", "15 días hábiles", "30 minutos") |
| Case consistency | drafts say "estamos escalando tu caso al equipo de …" only when the decision opens a case, with the team name from the policy |
| Policy gaps | MSG-010 (hours: no policy → person), MSG-182 (data deletion → privacy owner, cancellation steps still answered), MSG-006 (how to prepay step by step: partially covered → answered and a low-priority case) |
| Cost and latency | 13 drafts USD 0.18 (≈ 0.028 each, output tokens dominate: 600–970 per draft including thinking), 9–14 s per draft; classification replayed from cache at no cost; the whole 18-message run replays at USD 0.00 |

**Prompt iteration:** the first 13 drafts (draft-v1) were grounded and verified, but two of the
three `uncovered_points` were not gaps (a team reviewing a charge is the prescribed process,
not a missing policy) and some replies added policy facts nobody asked about. draft-v2 defines
an uncovered point as something the customer asked that no allowed section addresses, and
tells the model to answer what was asked. Same 18 messages: gaps 4 → 3, all real, no verifier
failure, cost unchanged.

**Incidents:** three routing defects, two caught by tests and one by reading the live records
(HOW_I_WORKED 3.6): the no-policy override swallowed the off-topic courtesy template, the
template was still attached to sales inquiries, and `auto_reply` decisions carried a queue.

**Key decisions (also in the plan's decision log, D8–D12):** "tú" register aligned with the
templates; only the allowed sections reach the drafting prompt and the verifier enforces
citations ⊆ allowed; habeas data routes the case even as a secondary reason; `policy_gap` means
what the knowledge base lacks, and a partially answered message opens a case so the promised
follow-up exists; one `effort` setting for both stages, `--effort low` as the cost lever.

**Full run (author, `python -m lumo_triage run --workers 4`, then replayed after the verifier fixes below):**

| Item | Value |
|---|---|
| Messages | 340; 0 unclassified |
| Actions | 145 `auto_reply_and_route`, 133 `auto_reply`, 50 `route_to_human`, 12 `close_no_reply` |
| Replies ready to send | 278 = 234 model drafts that passed the verifier + 44 fixed templates (22 fraud acknowledgements, 14 thanks, 5 off-topic, 3 greetings) |
| Verifier rejections | 4 of 238 model drafts (1.7 %): three mention "condonación" while denying it (the rule rejects any mention of debt forgiveness, even negated: a customer may anchor on the word, an agent decides) and one derived "marzo de 2026" from "2025" plus "el año siguiente" (arithmetic is not a citation). Each keeps its text as `rejected_text` and goes to a person. |
| Policy gaps | 54 messages: 13 reasons with no policy (fees and rates 8, hours 6, application status 1, habeas data 1…) plus 31 partially answered and routed (`GAP_ROUTED`) and 5 not answerable. The uncovered points name real holes: Nequi and Baloto as payment rails, certificates by e-mail, address changes, harassment stop requests, a debt certificate with capital/interest breakdown. |
| Queues | none 142, cx_general 56, cartera 53, pagos_conciliacion 39, fraude 22, pqr_legal 14, comercial 9, datos_privacidad 4, onboarding 1 |
| Draft length | 52–127 words, mean 87 |
| LLM usage | 230 live draft calls in the author's run (classifications replayed); 213,301 output tokens over the whole pipeline; recorded cost USD 7.73 for everything behind the output (USD 4.47 classification + USD 3.26 drafts, ≈ 0.014 per draft: v2 replies are shorter than the v1 sample) |
| Replay | the full run replays from cache with 0 live calls and USD 0.00 in about a minute |

**Incident (verifier false positives, found by reading the 11 rejections of the first full
run):** the placeholder check matched the Spanish word "todo" (5 drafts), number words written by
the customer ("dos veces", "tercera vez") were not credited to the message side (2 drafts), and
after adding ordinals, "el primer día" was read as the figure 1 (1 draft). Fixed with tests for
each phrase and replayed at no cost: 11 → 4 rejections, all four deliberate. HOW_I_WORKED 3.7.

**Commit:** `ecf360a` feat(ai): add routing engine, grounded drafting with verifier and end-to-end
run over the 340 messages

---

## Step 05 — Batch summary, single command, reproducibility  (2026-09-27)

**Goal:** the batch summary the assessment asks for, computed from the records and never from the
model; one command that sets up and runs; proof that the committed output is reproducible
without a key.

**Files:** `lumo_triage/summary.py` (`build_summary`, `render_markdown`), `lumo_triage/__main__.py`
(`run` now writes `batch_summary.json/.md`; new `summarize`; `--prune-cache`), `lumo_triage/llm.py`
(tracks the cache files a run used; `prune_untouched`), `schema.py` (`BatchSummary` gains
`replies_ready`, `cases_opened`, `policy_gap_details`), `run.ps1`, `run.sh`, `README.md`,
`tests/test_summary.py` (3 tests, including the reproducibility check). 154 tests, 1 skipped.

**Command(s):**
```powershell
python -m pytest -q
python -m lumo_triage run --workers 4 --prune-cache
.\run.ps1 --mode offline --limit 5 --out <scratch>\triage_results.jsonl
```

**Result:**

| Check | Evidence |
|---|---|
| Summary | `output/batch_summary.md`: 278 of 340 messages (81.8 %) leave with a reply ready; 195 open a case (145 also answered automatically, 50 need a person's answer); 12 closed; 54 touch a knowledge-base gap, listed in the customers' own words; 4 verifier rejections shown with their failed check; queue workload by priority; 7 low-confidence classifications listed |
| Reproducibility | `tests/test_summary.py::test_offline_replay_reproduces_the_committed_records` replays 40 messages offline from the committed cache and compares every field with the committed output; a full offline run makes 0 live calls, spends USD 0.00 and rewrites `triage_results.jsonl` identically (the summary differs only in its timestamp) |
| Single command | `run.ps1` exercised offline on 5 messages; `run.sh` mirrors it (syntax-checked with `bash -n`; a macOS/Linux execution is pending on David's machine or a reviewer's) |
| Cache hygiene | `--prune-cache` removed the 13 responses of the draft-v1 prompt that no request can reach any more; 568 files remain (325 classifications + 243 drafts), exactly the 568 responses a full replay uses |

**Key decisions:**
- The summary's figures come from the records only, so they are auditable line by line and a
  reviewer can regenerate them with `summarize` without a model.
- `cases_opened` counts both routed actions; the headline separates "answered and routed" from
  "needs a person's answer" because the CX team's workload is different in each case.
- `spent_this_run_usd` is null when the summary is regenerated from the file: the run that
  produced the records is the only one that knows what it spent.

**Commit:** `3726c3c` feat(ai): add batch summary, single-command runner, cache pruning and
reproducibility test

---

## Step 06 — Gold set, evaluation harness, adversarial fixtures  (2026-09-27, in progress)

**Goal:** measure the pipeline against human-confirmed labels and against adversarial inputs,
following Anthropic's `build-eval` guide adapted to this codebase (pytest + a Python harness;
the reference must not come from the model under test).

**Files:** `scripts/make_gold_set.py` (90 messages, deterministic: every hard case plus a
stratified fill, at least two per reason), `evidence/gold/prelabels_assistant.json` (the
assistant's independent reading of the 90 messages: reason, secondary reasons, priority,
action, note), `evidence/gold/gold_set.csv` (for the human: `ok` or corrections),
`scripts/make_draft_review.py` → `evidence/gold/draft_review.csv` (20 drafts for a human verdict),
`tests/fixtures/adversarial.jsonl` (10 fixtures: prompt injection ×3, empty text, English,
Portuguese, masked id, password request, fraud inside a data-change request, PII),
`lumo_triage/eval.py` (metrics, rubric judge on `claude-sonnet-5`, fixture checks, optional
model comparison and live stability run, Markdown report), `python -m lumo_triage eval`,
`tests/test_eval.py` (oracle and null checks on the metric functions). Also, from reading the
first eval: `known_gaps` patterns in `taxonomy.yaml` (password flows, address changes, unlisted
payment rails, unlisted certificates) applied by code after drafting, with tests. 160 tests.

**Command(s):**
```powershell
python scripts/make_gold_set.py; python scripts/make_draft_review.py
python -m lumo_triage eval --judge 5            # wiring check before the human labels
python -m lumo_triage run --workers 4           # replay with the known-gap detector
```

**Result before the human review (reference = assistant pre-labels, 0 rows reviewed):**

| Metric | Value |
|---|---|
| Primary reason | exact 86/90; within the primary+secondary set 90/90; macro-F1 0.949 |
| Priority | exact 82/90; within ±1 90/90; when different: 4 more urgent, 4 less urgent than the pre-label |
| Action | exact 77/90 (75 before the known-gap detector); 1 unsafe direction (MSG-389, a third complaint answered with a PQR acknowledgement instead of a person), 4 conservative |
| Adversarial fixtures | 10/10: injections flagged and routed with no reply, empty text closed without a model call, English and Portuguese classified with the right language and a Spanish reply, masked id kept masked, no password or PII echoed, fraud inside a data-change request still P0 |
| Judge wiring | 5/5 drafts ok on `claude-sonnet-5` (USD 0.017) |
| Known-gap detector | +7 cases opened on the full run (password ×3, address ×4 …), 61 messages with a named gap |

**Full evaluation (author's machine, `python -m lumo_triage eval --compare-model claude-haiku-4-5 --variance 30`,
reference still the assistant pre-labels, 0 rows reviewed):**

```text
gold=90 reviewed=0
reason exact=86/90 lenient=90/90 macro_f1=0.949
priority exact=82/90 within1=90/90  action exact=77/90 unsafe=1 conservative=4
judge claude-sonnet-5: overall_ok=54/57 cost=$0.1861
adversarial passed=10/10
stability: 30/30 same primary reason
comparison claude-haiku-4-5: exact=95.6% cost/msg=$0.0020
```

| Finding | Detail |
|---|---|
| Judge (Sonnet 5) rejected 3 of 57 verified drafts | MSG-130 and MSG-320 name the app section "Mi crédito", which is true per the knowledge base (`saldo_y_cuotas`) but comes from the drafting instructions, not from a cited section; MSG-278 says a radicado "quedó registrado" without giving one. All three passed the code verifier: the judge catches provenance and overclaims that regexes cannot. |
| Stability | 30 gold messages re-classified live: 30/30 same primary reason, mean confidence change 0.005 (USD 0.43). |
| Claude Haiku 4.5 as classifier | Same exact accuracy on the primary reason (86/90) at USD 0.0020 per message (7× cheaper) and 3.5 s p50 (vs 5.5 s); lenient 87/90 vs 90/90, macro-F1 0.940 vs 0.949. Its two misses are not equivalent to Opus's: MSG-389, a third complaint about an unresolved problem, became `sin_accion`, which the policy closes without a reply. |
| Cost of the evaluation | judge USD 0.19 + Haiku USD 0.18 + stability USD 0.43 ≈ USD 0.80; everything is cached, so re-running the eval after the human review costs nothing. |

**Incident:** the Haiku comparison made two live calls on every re-run and its exact accuracy
moved between 86/90 and 87/90. The trace showed the same message (MSG-220) called twice per
run; a probe (three live calls) showed Haiku writes a `reasoning_brief` longer than 300
characters for it every time, which the client-side pydantic check rejected (the API strips
string-length constraints), so the message was "unclassified" until a retry happened to fit and
the successful answer was never cached in time. Fix: length and range constraints are repaired
by truncation and clamping in `schema.py` (validators do not change the JSON schema, so the
committed cache keys are untouched; a new test pins a real cache key to the current prompt and
schema). The retry-on-invalid-output path stays for genuinely malformed answers.

**Reviewer:** `scripts/review_gold.py` shows one message (or draft) at a time in the terminal
and writes the CSV after every answer: Enter agrees with the pre-label, `r=` / `p=` / `a=` / `s=` /
`n=` correct it, `x=<issue>` rejects a draft. It avoids spreadsheet encodings and is resumable.

**Intermediate commits (work in progress, before the human review):** `0ecfa34`, `9ce4c86`
feat(ai): add evaluation harness, gold-set scaffolding, adversarial fixtures and known-gap detection.

**Human review (David, 2026-09-28):** 90 of 90 labels reviewed with the terminal reviewer,
89 confirmed and 1 corrected (MSG-119 "asdkjas hola" → `saludo_incompleto` / `auto_reply`:
a greeting deserves the "how can we help" template rather than a silent close); 20 of 20 drafts
judged sendable. Guide: `evidence/gold/LABELLING_GUIDE.md`.

**Final evaluation (`python -m lumo_triage eval --compare-model claude-haiku-4-5`, everything
from cache, USD 0):**

```text
gold=90 reviewed=90
reason exact=85/90 lenient=89/90 macro_f1=0.928
priority exact=82/90 within1=90/90  action exact=76/90 unsafe=1 conservative=5
judge claude-sonnet-5: overall_ok=54/57 cost=$0.1861 human_agree=19/20
adversarial passed=10/10
stability: 30/30 same primary reason
comparison claude-haiku-4-5: exact=95.6% cost/msg=$0.0020
```

The single correction moved reason exact from 86 to 85, lenient from 90 to 89 and action exact
from 77 to 76; the tier-0 change it suggests (gibberish plus a greeting → greeting template) is
recorded as a follow-up rather than applied after seeing the gold set. Judge-human calibration:
the reviewer accepted all 20 drafts, the judge rejected one of them (MSG-130) for naming an app
section that no cited policy section mentions. Full reading in `EVALUATION.md`.

**Incident:** after the review, `tests/test_eval.py` failed: it asserted at least two `ruido`
messages in the gold set, a property of the pre-labels that the reviewer's correction of
MSG-119 removed. The test now checks what a correction cannot change (90 unique ids, valid
labels, at least 20 reasons present, fraud present, the set either fully reviewed or untouched).
A test must not encode the labeller's opinion.

**Commits:** `0ecfa34`, `9ce4c86` (harness, gold scaffolding, fixtures, known gaps),
`f2dfd98` docs(ai): human-reviewed gold set, final evaluation report and labelling guide; the
test fix ships with step 7.

---

## Step 07 — Design document, HOW_I_WORKED, final checks  (2026-09-28)

**Goal:** close the documentation set and prove once more that the committed output is what the
single command produces.

**Files:** `DESIGN.md` (pipeline, record, policy-as-data, routing semantics, grounding and
verification, prompt versions, caching and replay, failure handling, scale and cost at 10,000
messages a day, security notes), `HOW_I_WORKED.md` §1, §2 and §4 completed (§3 has ten cases),
`IMPLEMENTATION_PLAN.md` D12 updated with measured costs and D13 added (evaluation choices),
`tests/test_eval.py` (the gold-set test no longer encodes the labeller's opinion).

**Command(s):**
```powershell
python -m pytest -q                     # 161 passed, 1 skipped (live, opt-in)
.\run.ps1 --mode offline                # full reproduction without a key: 0 live calls, USD 0.00
python -m lumo_triage eval --compare-model claude-haiku-4-5
```

**Result:** *(filled after David's final run)*

**Commit:** *(filled after commit)*
