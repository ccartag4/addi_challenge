# Implementation Plan — AI Challenge (contact triage and reply drafting)

> Evidence document. Written on 2026-09-27, **before** the first line of code, after reading the
> assessment, the challenge README, the taxonomy, the four knowledge-base files and all 340
> messages, and after profiling the messages quantitatively. Records the approach, the decisions
> taken (with the questions that led to them) and the step-by-step plan that `WORKLOG.md` traces.

---

## 1. Goal and grading lens

Build a component that takes one incoming customer message and returns a structured, reliable
result the ticketing system can act on: contact reason, priority, extracted details, whether it
can be auto-answered or needs a human (and which queue), and a grounded draft reply in Spanish
when it can be answered. Plus a summary of the whole batch.

Hard requirements from the assessment and the README:

1. **Reproducible on Addi's side**: a single command that sets up and runs the solution over
   `data/messages.jsonl`, writing its output to a file; the output of my own run is submitted.
2. **Generalises**: no answers hard-coded to the sample messages.
3. **Scale-aware**: the sample is 340 messages; production is ~10,000 per day.
4. **Taxonomy may be refined**, with every change explained.
5. **Replies grounded in `knowledge_base/`**, which is incomplete and inconsistent on purpose:
   a missing policy is a signal, not something to fill in.
6. **`HOW_I_WORKED.md`**: how the AI tools were used, how the output was validated, what to
   improve with more time. Every part must be defensible in the follow-up conversation.

Time budget for this challenge: roughly 3.5 to 4 hours of hands-on work.

---

## 2. Working method

Same method as the data challenge, which produced 19 traceable steps there:

| Practice | How it is applied |
|---|---|
| **Human runs, AI explains** | David executes every command; the assistant gives the goal, the command and what to look for. |
| **AI drafts, human approves** | Code, prompts, schemas and tests are drafted by the assistant and reviewed line by line before they run; corrections feed `HOW_I_WORKED.md`. |
| **One step, one worklog entry, one commit** | `WORKLOG.md` mirrors the data challenge's format. |
| **Evidence committed** | Profiling, evaluation reports, prompt versions, LLM call traces, sample outputs under `evidence/`. |
| **Validate before handing over** | The assistant validates every component in a scratch copy from a clean state before David runs it; validations that pass on stale artefacts are treated as failures (lesson from the data challenge, AI log 3.4). |
| **Determinism where the model is not needed** | Rules, extraction, routing and verification are code, tested with `pytest`; the model classifies and drafts. |

---

## 3. Decision log — questions asked and answers given (2026-09-27)

| # | Question | Options offered | Decision | Rationale |
|---|---|---|---|---|
| D1 | Which credential for live testing? | Ask Addi for a key · use a personal key · another provider | **Ask Addi for the key now (the assessment offers one) and use a personal Anthropic key meanwhile, so the work is not delayed.** | The key is read from the environment (`ANTHROPIC_API_KEY`) or from a local `.env` file that is git-ignored; `.env.example` documents it. No key is ever committed. Addi's key, when it arrives, replaces the personal one with no code change. |
| D2 | Which model? | Opus 5 for everything · Sonnet 5 · Haiku 4.5 worker + Opus 5 judge | **David asked for a recommendation. Recommended and adopted: Claude Opus 5 (`claude-opus-5`) as the model of the submission, for classification, drafting and the LLM judge; the model is a configuration value per stage, and a measured comparison with Claude Haiku 4.5 on the gold set is planned as evidence for the 10,000/day discussion.** | Reasons: (a) the reviewers judge the quality of what they read, and the run over 340 messages costs a few dollars on any model; (b) Anthropic's guidance is Opus 5 by default, downgrading for cost is a business decision that should be shown with numbers, not assumed; (c) the two-tier pattern (cheap classifier, strong judge) is the standard answer for volume, and it is far more convincing as a measured result ("Haiku loses X points of accuracy at one fifth of the cost") than as a claim. Estimated production cost at 10,000 messages/day with prompt caching: Opus 5 ≈ 145 USD/day, Sonnet 5 ≈ 58, Haiku 4.5 ≈ 29; the Batch API halves each. |
| D3 | Test and evidence tooling? | pytest + own harness per Anthropic's eval guide · plus promptfoo · pytest only | **pytest + an evaluation harness built along Anthropic's `build-eval` guide.** | Everything stays in Python with no extra runtime for the reviewer. Gold set, per-reason metrics, action agreement, confusion matrix, entity precision/recall, LLM-judge rubric for drafts calibrated against human labels, and a Markdown report. promptfoo (Node 24 is available) stays as an optional extra if time allows. |
| D4 | How is the gold set built? | David labels 80–100 with AI pre-labels · labels all 340 · LLM judge only | **David labels 80–100 stratified messages; the assistant pre-labels, David confirms or corrects.** | Human-verified labels are the strongest validation evidence and take about 30 minutes; a self-graded LLM would be a fair objection from the reviewers. |

Decisions taken by the assistant and stated here (David may override):

| # | Decision | Why |
|---|---|---|
| D5 | **Offline replay mode.** Every LLM response is cached on disk keyed by a content hash of (model, prompt, message) and committed under `cache/`. The single command runs from the cache when there is a hit and calls the API otherwise; with no key and no cache hit it fails with a clear message. | Addi can reproduce the submitted output byte for byte without a key, and can run live with theirs. It also makes the pipeline deterministic across re-runs and cheap to iterate. |
| D6 | **Single command = `run.ps1` / `run.sh`** that creates the virtual environment if missing, installs pinned dependencies, runs the pipeline over `../data/messages.jsonl` and writes `output/triage_results.jsonl` plus `output/batch_summary.json` and `.md`. | The assessment asks for one command that sets up *and* runs. |
| D7 | **Python 3.11–3.13, Anthropic Python SDK, `pydantic` schemas, structured outputs (`output_config.format`), prompt caching of the stable prefix, refusal fallbacks enabled.** | First-party SDK, schema-validated JSON without parsing tricks, and the stable prefix (taxonomy, policies, few-shots) is the bulk of every request. |
| D8 | **Deliverables in English; replies to customers in Spanish (Colombian register, "usted").** | Consistent with the data challenge and the README's note that replies must be in Spanish. |

---

## 4. What the data shows (profiling of the 340 messages, 2026-09-27)

Evidence file: `evidence/message_profiling.md` (regenerated in step 1).

| Finding | Figure | Design consequence |
|---|---|---|
| Channels | chat 119, WhatsApp 115, email 106 | sender formats differ by channel (phone, `cliente_NNNN`, email); channel is an input to the reply register |
| Timestamps | 40 without offset, 300 with `-05:00`, 2026-05-04 to 05-15 | normalise to UTC-5 (Bogotá) |
| Duplicates | 2 exact pairs once punctuation-only texts are excluded (the first profiling pass said 3, see step 02 in the worklog); 55 messages (16 %) in 40 near-duplicate pairs (token Jaccard ≥ 0.6) | content-hash cache; near-duplicate grouping reported in the batch summary; at 10k/day this is real money |
| Length | median 88 characters, max 247 | the system prompt dominates cost, so prompt caching matters more than model choice per message |
| Sensitive data | credit numbers 4 %, document numbers 2 %, amounts 2 %, transaction references 1 %, explicit dates 8 %, banks or payment rails 8 %, 2 deliberately masked identifiers (`1.0xx.xxx.xxx`) | deterministic extraction verified verbatim against the text; never complete a masked value; never echo a document number in a reply |
| Multi-intent | 16 messages (5 %) with explicit markers ("y de paso", "además", "1) … 2)") | primary reason plus secondary reasons |
| Urgency and risk | 71 with urgency words; 24 fraud/security signals; 22 economic hardship; 3 legal threats (Superintendencia, harassment) | priority is a separate dimension from the reason, driven by flags |
| Asks for a human | 15 | deterministic rule: always routed to a person |
| Out of scope | 28 (iPhones, Rappi, pizzería, weather, capital of France, hours of a branch) | distinguish *other business* (sales inquiry) from *unrelated* and from *general Lumo information* (hours, phone line) |
| Noise | 17 greetings-only, thanks-only or gibberish | tier-0 rules, no model call |
| Taxonomy gaps | interest and fee disputes 7, application status 1, address change 4, habeas data 2, prepayment/settlement quotes 5 | new reasons or sub-reasons, each justified in `TAXONOMY.md` |
| Knowledge-base trap | 12 messages talk about a "contraseña"; the policy says login is document + OTP, no password | the draft must not invent a password-reset flow: policy gap, route to support |
| Rules alone are not enough | 24 messages match no keyword even with the v2 buckets (28 with the v1 list); the rest spread flatly over ~20 buckets | rules handle noise and extraction; classification needs the model |
| Encoding | 0 mojibake in the file | an earlier "mojibake" observation was a PowerShell console artefact, corrected here |

---

## 5. Architecture

```mermaid
flowchart LR
    IN["messages.jsonl<br/>340 msgs, 3 channels"] --> N["1. Normalise<br/>UTC-5, unicode NFC, whitespace,<br/>content hash, near-dup groups"]
    N --> R["2. Deterministic layer<br/>regex entity extraction verified verbatim,<br/>masked-value detection, tier-0 rules<br/>(greeting / thanks / gibberish / human requested)"]
    R -- "tier-0 hit" --> P["4. Routing policy (YAML)<br/>reason x flags x confidence -> action, queue, SLA"]
    R -- "needs the model" --> C["3. LLM classification<br/>Claude Opus 5, structured output (pydantic):<br/>primary + secondary reasons, priority, flags,<br/>entities confirmed, confidence, summary"]
    C --> P
    P -- "auto_reply / auto_reply_and_route" --> D["5. Grounded drafting<br/>KB sections selected by reason,<br/>Spanish reply citing section ids,<br/>or policy_gap when uncovered"]
    D --> V["6. Verifier (code)<br/>schema, citations exist, numbers in reply<br/>exist in cited KB text, no forbidden promises,<br/>no customer document echoed, length"]
    V -- "fails" --> H["route_to_human"]
    V -- "passes" --> OUT["triage_results.jsonl"]
    P -- "route_to_human / close" --> OUT
    H --> OUT
    OUT --> S["batch_summary.json / .md<br/>volumes, auto-answer rate, policy gaps,<br/>duplicates, anomalies, cost"]
    CACHE[("cache/ (committed)<br/>LLM responses by content hash")] -. "hit = no API call" .- C
    CACHE -. "" .- D
    TRACE[("evidence/llm_calls.jsonl<br/>tokens, cache hits, latency, cost")] -. "" .- C
```

Principles: the model decides *what the message is*; code decides *what to do with it*; code
verifies *what the model wrote*. Every LLM call is cached, traced and schema-validated.

### 5.1 Output schema (per message, JSON line)

`id`, `channel`, `received_at_utc`, `dedup {content_hash, duplicate_of, near_duplicate_group}`,
`classification {primary_reason, secondary_reasons[], confidence, out_of_scope_kind}`,
`priority {level P0–P4, sla_hours, rationale}`,
`flags {fraud_or_security, requests_human, legal_threat, collections_harassment,
vulnerable_customer, prompt_injection_suspected, pii_present}`,
`entities {credit_number, document_number, amount, payment_date, transaction_reference,
payment_method_or_bank, masked_values[]}` (every value verified to appear verbatim in the text),
`sentiment`, `language`, `summary`,
`decision {action, queue, reason_codes[], policy_coverage full|partial|none, policy_gap}`,
`draft_reply {text|null, kb_citations[], verifier {passed, checks[]}}`,
`processing {rules_applied[], model, input_tokens, output_tokens, cache_hit, latency_ms,
cost_usd, pipeline_version}`.

### 5.2 Taxonomy v2 (to be finalised in step 1, justified in `TAXONOMY.md`)

Keep the 17 original reasons. Proposed additions, each backed by messages in the sample:
`intereses_y_cargos` (regular interest rate, "cuota de manejo", unauthorised insurance charge;
distinct from late-interest `mora_intereses`), `pago_anticipado` (prepayment and early
settlement quotes; the KB covers it, so it is auto-answerable), `estado_solicitud` (application
status; not in the KB), `informacion_general` (hours, phone line, branches; Lumo-related but not
in the KB), `privacidad_habeas_data` (what data do you hold, delete my data; legal handling),
`saludo_incompleto` (greeting only: ask what they need), `sin_accion` (thanks/closure: close),
`ruido` (gibberish/test). Cross-cutting **flags** instead of reasons: `requests_human`,
`collections_harassment`, `legal_threat`, `vulnerable_customer`. `fuera_de_alcance` keeps
unrelated topics and gets `out_of_scope_kind` (other_business_inquiry vs unrelated).

### 5.3 Priority and routing (deterministic, YAML)

P0 critical: fraud, lost/stolen phone, identity theft, hacked account → `fraude` queue, human,
immediate. P1 high: double charge or refund, bureau-report dispute with stated impact, legal
threat, collections harassment, imminent reporting, vulnerable customer → human. P2 normal:
payment not applied, cannot pay / refinance, login and app issues, formal complaints. P3 low:
information, certificates, data updates, feedback. P4 none: noise, closures. Actions:
`auto_reply`, `auto_reply_and_route`, `route_to_human`, `close_no_reply`. Queues: `fraude`,
`cartera`, `pagos_conciliacion`, `soporte_tecnico`, `pqr_legal`, `datos_privacidad`,
`onboarding`, `comercial`, `cx_general`, `none`. Low confidence (< 0.6) or any verifier failure
→ human.

### 5.4 Grounding rules for drafts

KB sections get stable ids (`pagos_y_cuotas.metodos_de_pago`, …); each reason maps to allowed
sections; the drafting prompt receives only those sections and must cite them; the verifier
checks that every number or time span in the reply (5 días, 30 minutos, 24 horas, 15 días
hábiles, una vez por año, …) appears in the cited text, that no forbidden promise appears
(condonación, devolución confirmada, borrar el historial), and that no customer document number
is echoed. Reasons with `policy_coverage = none` (password reset, address change, application
status, hours) never get a draft; they get `policy_gap` and a human.

---

## 6. Evaluation plan (Anthropic `build-eval` guide)

| Step | What |
|---|---|
| What is evaluated | reason accuracy (primary; secondary as set overlap), priority agreement (exact and ±1), action agreement, queue agreement, entity extraction precision/recall, draft groundedness and safety |
| Prompts source | the 340 real messages; gold set = 90 stratified by rough reason bucket and channel, pre-labelled by the assistant, confirmed or corrected by David in a CSV |
| Grading | exact match for reason/action/queue; ±1 tolerance reported for priority; F1 for entities; LLM judge (Opus 5) with a written rubric for drafts (grounded, correct, right tone, no forbidden promises) calibrated against 20 human-judged drafts; adversarial fixtures (prompt injection inside a message, empty text, English and Portuguese messages, masked identifiers) |
| Runnable | `python -m lumo_triage eval` → `evidence/eval_report.md` with metrics, confusion matrix, error analysis and measured cost; optional second run with `--model claude-haiku-4-5` for the cost/quality comparison |
| Determinism | two offline runs must be byte-identical; a live re-run of 30 messages measures classification variance |

---

## 7. Documentation set

| File | Purpose |
|---|---|
| `README.md` | the single command, options (`--mode live/offline`, `--model`), where the output is |
| `IMPLEMENTATION_PLAN.md` | this document |
| `WORKLOG.md` | one entry per step with commands, results, findings, commit |
| `DESIGN.md` | architecture (Mermaid), output schema, routing policy, prompt versions, grounding rules, scale and cost notes |
| `TAXONOMY.md` | taxonomy v2 with the rationale and sample message ids for every change |
| `EVALUATION.md` | gold-set method, metrics, confusion matrix, error analysis, judge calibration, adversarial results |
| `HOW_I_WORKED.md` | required: tools used, validation, where the AI was wrong, improvements with more time |
| `output/` | `classifications.jsonl` (step 3), then `triage_results.jsonl`, `batch_summary.json`, `batch_summary.md` from my run |
| `evidence/` | message profiling, `llm_calls.jsonl` (one line per live call), `classification_run.md` (generated by `scripts/summarize_classifications.py`), eval reports, pytest report |
| `cache/` | committed LLM responses for offline replay, one JSON per (model, purpose, message, request fingerprint) |

---

## 8. Step-by-step plan

| Step | Content | Estimate |
|---|---|---|
| 0 | venv, dependencies, `.env`, package skeleton, plan committed | 20 min |
| 1 | profiling evidence, taxonomy v2, routing YAML, pydantic schema | 30 min |
| 2 | normalisation, dedup, entity extraction, tier-0 rules + pytest | 30 min |
| 3 | LLM classification: cached prompt, structured output, retries, trace, offline cache | 35 min |
| 4 | grounded drafting + verifier + KB section ids | 35 min |
| 5 | batch summary, CLI single command, full run over the 340 → `output/` | 20 min |
| 6 | gold labelling (pre-labels → David), eval harness, report, optional Haiku comparison | 45 min |
| 7 | `DESIGN.md`, `EVALUATION.md`, `HOW_I_WORKED.md`, `README.md`; final run; commit | 25 min |

Total ≈ 4 h, above the 2.5–3 h slice the assessment implies for this challenge. The scale-down
levers, in order, if time runs out: skip the Haiku comparison, reduce the gold set to 60, skip
adversarial fixtures beyond prompt injection.

---

## 9. Definition of done

- One command from a fresh clone (with or without a key) produces `output/triage_results.jsonl`
  and the batch summary; the committed output equals a fresh offline run.
- Every result validates against the schema; every draft passed the verifier or was replaced by
  a human route with a reason code.
- `EVALUATION.md` reports metrics on the human-confirmed gold set with the confusion matrix.
- `TAXONOMY.md` explains every change to the taxonomy with message ids.
- `HOW_I_WORKED.md` lists the tools, the validation, at least two AI errors and the improvement
  backlog.
- `WORKLOG.md` has one entry per step and each maps to a commit; no key or secret in the repo.
