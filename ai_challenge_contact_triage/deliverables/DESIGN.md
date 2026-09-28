# Design

How the triage component works, why it is shaped this way, and what changes at 10,000 messages
a day. The decision log (D1–D13) is in `IMPLEMENTATION_PLAN.md`; the measurements are in
`EVALUATION.md` and `output/batch_summary.md`.

## 1. Principle

**The model decides what the message is; code decides what to do with it; code verifies what
the model wrote.** Everything the model produces is schema-validated, cached, traced and
replayable. Everything that can be decided by a rule or a policy file is decided there, so the
CX team can change routing, priorities, templates and known policy gaps without touching a prompt.

## 2. Pipeline

```mermaid
flowchart LR
    IN["messages.jsonl<br/>340 msgs · chat / email / WhatsApp"] --> N["1 normalise<br/>UTC (naive = Bogotá), NFC,<br/>content hash, exact + near duplicates"]
    N --> R["2 rules<br/>tier-0 (noise, greeting, closure)<br/>flag detectors · verbatim entities"]
    R -- "tier-0 / duplicate" --> P
    R --> C["3 classify · Claude Opus 5<br/>structured output = Classification<br/>system prompt rendered from taxonomy.yaml (cached)"]
    C --> F["3b finalize (code)<br/>entities merged + re-verified · flags OR-ed<br/>human-as-flag · out-of-scope kind"]
    F --> P["4 route · routing.yaml<br/>overrides → defaults → priority<br/>reply source · allowed KB sections"]
    P -- "template" --> V
    P -- "draft allowed" --> D["5 draft · Claude Opus 5<br/>only the allowed KB sections<br/>citations + uncovered points"]
    D --> V["6 verify (code)<br/>citations · numbers · phrases · echoes<br/>length · language · placeholders · contacts"]
    V -- "pass" --> G["7 known gaps (patterns)"]
    V -- "fail" --> H["route_to_human<br/>text kept as rejected_text"] --> G
    P -- "no reply / close" --> G
    G --> OUT["triage_results.jsonl"]
    OUT --> S["8 summary (code)<br/>batch_summary.json / .md"]
    CACHE[("cache/<br/>one JSON per request fingerprint")] -. "read before any call" .- C
    CACHE -. "" .- D
    TRACE[("evidence/llm_calls.jsonl<br/>one line per live call")] -. "" .- C
```

| Stage | Module | Input → output | Deterministic? |
|---|---|---|---|
| 1 normalise | `normalize.py` | raw line → `Message` (UTC time, NFC text, hash, duplicate links, near-duplicate group) | yes |
| 2 rules | `rules.py`, `extract.py` | text → tier-0 verdict, flag hits, entities that appear verbatim | yes |
| 3 classify | `classify.py`, `llm.py` | message → `Classification` (reasons, confidence, flags, entities, sentiment, summary) | model; cached |
| 3b finalize | `classify.finalize` | model output + rule output → adjusted classification with `POST_*` codes | yes |
| 4 route | `routing.py`, `policy/routing.yaml` | classification → priority, action, queue, reply source, allowed sections | yes |
| 5 draft | `draft.py`, `kb.py` | message + triage + allowed sections → `DraftOutput` (reply, citations, uncovered points) | model; cached |
| 6 verify | `verify.py` | reply + citations → pass/fail per check | yes |
| 7 known gaps | `routing.known_gaps` | reason + text → named policy holes; opens a case if the reply was automatic | yes |
| 8 summary | `summary.py` | records → batch summary | yes |

## 3. The record

One JSON line per message (`schema.py`, pydantic, `extra="forbid"` everywhere):

- `classification`: what the model said, after the code adjustments; `null` only when the
  model failed (refusal after fallback, invalid output twice, API unavailable, offline miss),
  in which case the decision routes to a person and `processing.llm_error` says why.
- `decision`: `priority` P0–P4 with `sla_hours`, `action`, `queue`, `policy_coverage`,
  `policy_gap`, and `reason_codes`: every override, bump, post-processing and verifier code
  that fired, in order. The codes are the audit trail: `OVR_FRAUD`, `BUMP_VULNERABLE_CUSTOMER`,
  `POST_HUMAN_TO_FLAG`, `DRAFT_VERIFIED`, `GAP_ROUTED`, `VERIFIER_NUMBERS`, `KNOWN_GAP`, …
- `draft_reply`: `text` only when sendable; `source` llm / template / none; `kb_citations`
  (section ids that resolve to a file and a heading); `verifier` with every check; and
  `rejected_text` for a model draft that failed, kept for the agent and never sent.
- `processing`: pipeline version (with both prompt versions), rules applied, model requested
  and served, effort, live calls, tokens by kind, cache replays, latency, cost, error.

## 4. Taxonomy and policy as data

`policy/taxonomy.yaml` (25 reasons: the CX team's 17 plus 8 added, see `TAXONOMY.md`) declares
for each reason its knowledge-base sections, `policy_coverage` (full / partial / none), default
action, default queue, base priority, reply source, example message ids, and `known_gaps`
patterns. `policy/routing.yaml` declares the overrides (in evaluation order), priority bumps,
verifier rules, reason→template mapping, template citations, queue labels and the fixed Spanish
templates. Three consumers read the same files: the classifier prompt, the routing engine and
the tests (`tests/test_policy_consistency.py`), so a reason cannot exist in one place and not the
others, a cited section must exist as a markdown heading, and a reason without policy can never
receive a model draft.

## 5. Routing semantics

1. **Overrides, first match wins** (`OVR_INJECTION`, `OVR_FRAUD`, `OVR_HUMAN`, `OVR_LEGAL`,
   `OVR_HABEAS`, `OVR_LOW_CONFIDENCE`, `OVR_NO_POLICY`, `OVR_OOS_SALES`). An override sets the
   action, the queue (or "the reason's queue, else cx_general"), a minimum priority, whether a
   draft is forbidden, a template, and extra sections the draft may cite.
2. **Priority**: the most urgent base priority among primary and secondary reasons
   (`PRIO_SECONDARY_*`), raised to the override's minimum, then one level per flag bump
   (`vulnerable_customer` to at least P1, `imminent_deadline`, `repeat_contact`), never past P0.
3. **Reply source**: an override template, else the reason's template, else a model draft when
   the reason has coverage and the action is automatic; an automatic action with no possible
   reply degrades to `route_to_human` (`NO_REPLY_SOURCE`).
4. **After drafting**: a failed verifier check routes to a person; `can_answer = false` routes
   with the model's uncovered points as the gap; a partially answered request keeps the draft
   and opens a case (`GAP_ROUTED`); a known-gap pattern does the same by code (`KNOWN_GAP`).
5. **Queues** only exist when a person is involved; `auto_reply` carries `queue = none`.

Flags are the cross-cutting signals (fraud, wants a person, legal threat, collections
harassment, vulnerability, imminent deadline, repeat contact, prompt injection, PII). Rules and
model both set them; the record keeps the union.

## 6. Grounding and verification

The drafting prompt receives only the sections bound to the message's reasons (plus the PQR
section when a legal flag fires). The model must cite the ids it used and list what the
sections do not cover. Then code checks:

| Check | Rule |
|---|---|
| citations | at least one; all inside the allowed set |
| numbers | every numeral, number word ("cinco días") or ordinal ("tercera vez") in the reply appears in a cited section or in the customer's message; "primer día" is idiom, not a figure |
| forbidden_phrases | no refund/forgiveness/history-deletion/non-reporting promises, no credential requests (accent-insensitive) |
| no_document_echo | the customer's document number and any card number never appear |
| length | 8–160 words |
| language | Spanish function words present, no English markers |
| no_placeholders | no brackets, braces, `XXX`, upper-case `TODO` |
| contact_details | e-mails and URLs only if a cited section contains them |

Templates skip the citation check (they cite fixed sections) and pass the rest. The verifier
rejected 4 of 238 drafts in the submitted run; the rubric judge, which reads for provenance and
overclaiming, rejected 3 more of the 57 it graded (EVALUATION.md §4).

## 7. Prompts

| Prompt | Version | Notes |
|---|---|---|
| classifier system prompt | `classify-v1` | rendered from `taxonomy.yaml` (reasons with Spanish names, descriptions and notes; flags; out-of-scope kinds), 14 decision rules, 13 synthetic boundary examples; ≈ 7,400 tokens, cached; no dataset text |
| classifier user turn | — | `<customer_message id channel>` with the text HTML-escaped as data |
| drafting system prompt | `draft-v2` | grounding rules, "never" list, style; v1 → v2 restricted `uncovered_points` to what the customer asked and no section covers, and told the model to answer what was asked |
| drafting user turn | — | message, triage context (reasons, flags, verified entities, whether a case is opened and with which team), allowed `<kb_section>` blocks |
| judge (evaluation only) | — | rubric with five booleans and issues, structured output, `claude-sonnet-5` |

Model settings: `claude-opus-5` with default adaptive thinking and `effort = medium`
(configurable); no sampling parameters (rejected on this model); `fallbacks = "default"` so a
safety-classifier refusal is re-run server-side on Anthropic's recommended substitute;
`max_tokens` 4096, doubled once on truncation; one retry on output that does not validate.

## 8. Caching, tracing, replay

Every structured call is keyed by a fingerprint of (model, effort, system prompt, user turn,
JSON schema) and stored under `cache/<model>/<purpose>/<id>__<key>.json`. A run in `auto` mode
replays hits and calls the API only for misses; `offline` forbids calls; `live` forces them
but still writes. A prompt or schema change changes the keys, so stale entries are inert and
`run --prune-cache` removes them. A test pins the key of a real message to its committed file,
so drift cannot go unnoticed. Each live call appends a line to `evidence/llm_calls.jsonl`
(usage by token kind, cache activity, latency, request id, model served, outcome) and never
the customer text or the key. Pydantic validators repair length and range violations by
truncation instead of rejecting a correct answer; the schema sent to the API is unchanged.

Consequences: the committed output reproduces byte for byte without a key (a test replays
40 messages and compares every field), a full replay costs nothing, and the classification is
stable across live runs (30/30 on the gold set).

## 9. Failure handling

| Failure | Behaviour |
|---|---|
| Rate limit, 5xx, connection error | SDK retries with backoff (4); then the message is recorded with `llm_error` and routed to a person |
| Safety refusal | server-side fallback model; if the whole chain refuses, `LLMRefusal` → routed to a person |
| Output does not validate | one retry; then `LLMOutputInvalid` → routed to a person |
| Truncated output | `max_tokens` doubled once |
| Offline cache miss | `OfflineCacheMiss` → routed to a person, error recorded |
| Prompt injection in the text | flag by rule or model → `OVR_INJECTION`: never auto-answered; the text is data inside a tag in both prompts |
| Exact duplicate | reuses the original's classification (`DEDUP_REUSED`), no call |

## 10. Scale: 10,000 messages a day

Measured on the submitted run (Opus 5, effort medium, prompt cache warm):

| Item | Value |
|---|---|
| Classification | USD 0.014 and ≈ 5.5 s p50 per message; 7,400 cached prefix tokens per call |
| Draft | USD 0.014 and ≈ 10 s p50 per message; 69 % of messages get a model draft |
| Whole pipeline | USD 0.0225 per message ≈ **USD 225 per 10,000 messages**; ≈ 0.6 live calls per second at 4 workers |
| Haiku 4.5 for classification | USD 0.002 per message, 3.5 s p50, same exact accuracy on 90 gold messages with one dangerous miss (EVALUATION.md §5) |

What changes at that volume:

- **Batch API for non-urgent traffic.** E-mail and any message that is not P0/P1 can go through
  the Message Batches API at half price with hours of latency; chat and WhatsApp stay
  synchronous. The `fallbacks` parameter is not available on Batches, so refusals need the
  client-side handling already in place.
- **Two-tier classification, measured first.** Haiku 4.5 behind the same rules, threshold and
  verifier would cut the classification bill by 7×; the deciding metric is the unsafe count on a
  larger gold set, not accuracy.
- **Concurrency and limits.** Async workers with a bounded pool sized to the rate-limit tier;
  the one-warm-up-then-fan-out pattern keeps the prompt cache hit rate at 98 %; cache reads do
  not count toward input-token limits on the Claude API.
- **Operations.** The trace already yields the dashboards a CX lead needs: verifier rejection
  rate, policy-gap rate by reason, cost per queue, latency; alerts on `llm_error` and on a
  falling cache-read share (the signature of a silent prompt change).
- **Knowledge base as a versioned artefact.** Section ids are already stable; a CI test fails
  when a heading disappears; the same mechanism can pin a KB version into each record.
- **Privacy.** Traces carry no customer text; records carry the text and verified entities and
  should follow the ticketing system's retention; document numbers are never echoed in replies.

## 11. Security notes

- The API key lives in the environment or a git-ignored `.env`; nothing in the repository or
  the traces contains it.
- Customer text is data in both prompts (escaped inside a tag) and the classifier is asked to
  flag instructions; an injection never reaches an automatic reply (`OVR_INJECTION`, fixtures
  ADV-01, ADV-02, ADV-10).
- Drafts cannot ask for credentials (forbidden phrases) and cannot echo a document or card
  number (verifier); masked identifiers stay masked (`masked_values`).
