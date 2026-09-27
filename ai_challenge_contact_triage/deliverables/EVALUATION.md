# Evaluation

How the triage component was measured, what the numbers say, and what they do not. The figures
are produced by `python -m lumo_triage eval` and written to `evidence/eval_report.md` and
`evidence/eval/eval_results.json`; this document explains the method and reads the results.
It follows Anthropic's `build-eval` guide (inputs the author reviewed, grading that matches the
output's shape, a runnable script, cost measured from real usage), adapted to a Python codebase
with pytest and no external framework.

## 1. What is evaluated

One flow: a customer message goes in, a `TriageRecord` comes out. Four things are graded:

| Output | How it is graded | Why this way |
|---|---|---|
| Primary contact reason | exact match against the gold label; a lenient match that also accepts a pipeline primary listed among the gold secondary reasons; per-class precision, recall and F1; confusion pairs | closed label set, so a programmatic check measures the answer, not the phrasing; multi-intent messages have more than one defensible order |
| Priority (P0–P4) | exact and within ±1 level; direction of the difference | ordinal; being one level off in the safe direction is a different error from being one level off in the risky direction |
| Action | exact; the *unsafe* direction (gold wants a person, pipeline answers alone) reported separately from the *conservative* one | the CX team cares about the unsafe count first |
| Draft replies | code verifier pass rate (eight checks), a rubric judge with structured output on `claude-sonnet-5`, calibrated against a human review of 20 drafts | free text has many valid phrasings; a judge is needed for grounding and tone, and it must not be the model under test |

Plus three checks that are not label comparisons: ten adversarial fixtures with fixture-specific
assertions, a live re-classification of 30 messages for stability, and a classification-only
run of the gold messages with a cheaper model for the cost discussion.

## 2. Gold set

`evidence/gold/gold_set.csv`, 90 of the 340 messages, selected deterministically by
`scripts/make_gold_set.py`: every case the pipeline found hard (model confidence below 0.70,
disagreement with the taxonomy example ids, drafts rejected by the verifier, the
gibberish-with-words message) and then a stratified fill so that every one of the 25 reasons
appears at least twice and the rest follows volume.

The reference labels are **not** the pipeline's output. The assistant read the 90 messages and
the policy and wrote reason, secondary reasons, priority, action and a note per message
(`evidence/gold/prelabels_assistant.json`), without looking at the pipeline's predictions for
those rows. The human reviewer then confirms (`gold_note = ok`) or corrects the `gold_*` cells;
`reviewed` in the report counts rows with a confirmation or a correction. Until that column is
filled the metrics measure agreement between two independent readings of the policy (the
assistant's and the pipeline's), which is informative but is not human validation; the report
states the number of reviewed rows on its first line for that reason.

Labelling policy: the primary reason is the request that decides who handles the message; when
there are two, the one that opens a case or the one the customer wrote first, the other goes to
`secondary`. Priority follows the definitions in `taxonomy.yaml` (P0 active security risk, P1
money wrongly taken / legal exposure / imminent reporting / vulnerable customer, P2 blocked from
paying or using the product and formal complaints, P3 information, P4 nothing to do). Action
follows the policy: `auto_reply` when the knowledge base answers and nobody needs to act,
`auto_reply_and_route` when a case must be opened, `route_to_human` when a person must answer,
`close_no_reply` for noise and closures.

## 3. Results (2026-09-27, reference = assistant pre-labels, 0 rows reviewed)

| Metric | Value |
|---|---|
| Primary reason, exact | 86/90 (95.6 %) |
| Primary reason, within the gold primary+secondary set | 90/90 |
| Macro-F1 over the 25 classes present | 0.949 |
| Priority exact / within ±1 | 82/90 / 90/90; when different: 4 more urgent than gold, 4 less urgent |
| Action exact | 77/90; unsafe 1; conservative 4; `auto_reply` vs `auto_reply_and_route` 8 |
| Drafts in the gold set | 61 model drafts: 57 passed the verifier, 4 rejected; 12 templates |
| Judge (`claude-sonnet-5`, 57 drafts, USD 0.19) | grounded 54, answers the request 57, no forbidden promise 57, tone ok 57, overall ok 54 |
| Adversarial fixtures | 10/10 |
| Stability (30 messages re-classified live, USD 0.43) | 30/30 same primary reason; mean confidence change 0.005 |
| `claude-haiku-4-5` as classifier | exact 86/90, lenient 87/90, macro-F1 0.940; USD 0.0020 per message vs 0.0140; p50 3.5 s vs 5.5 s |

The per-class table, the confusion pairs, every disagreement with its text and the fixture
checks are in `evidence/eval_report.md`. The section is regenerated after the human review;
the numbers above will be replaced by the reviewed ones and the differences noted here.

## 4. Error analysis

**Reason (4 exact disagreements, 0 lenient).** All four are two-intent messages where the
pipeline put the other request first: a formal complaint about late interest classified as
`mora_intereses` (MSG-130), a customer who wants an agent *and* asks for the phone line
classified as `informacion_general` (MSG-186), a statement request with a pending payment
classified as `certificados_extractos` (MSG-249), and a hardship message that opens with a
balance question classified as `consulta_saldo_cuotas` (MSG-298). In every case the gold primary
appears among the pipeline's secondary reasons. The cost of the wrong order is routing: two of
the four ended as `auto_reply` where the gold opens a case (Cartera, Pagos).

**Priority (8 differences, all within one level).** Four are one level *below* the gold on
"money wrongly taken" cases: two double charges (MSG-012, MSG-176) and two bureau disputes with
stated impact (MSG-259, MSG-297) stay at the reason's base P2 because no flag encodes "money at
risk" or "dispute with impact". Three are one level *above* on multi-intent messages where a
secondary reason raised the priority (the policy takes the most urgent of primary and
secondary). One is the phishing report (MSG-329): the policy makes every security signal P0,
the pre-label says P1 because the account is not compromised yet.

**Action (13 differences).** Eight `auto_reply_and_route → auto_reply`: the pipeline answered
without opening a case where the reviewer would open one, mostly app and password issues
(MSG-166, MSG-368, MSG-381, MSG-284) and an e-mail that keeps arriving after an update
(MSG-038). After this finding, `taxonomy.yaml` gained `known_gaps`, patterns for policy holes
the taxonomy already named (password flows, address changes, unlisted payment rails, unlisted
certificates); the pipeline now opens a case when one matches, which fixed two of the eight
(77/90 from 75/90) without a model call. Three `auto_reply_and_route → route_to_human` are the
verifier rejecting drafts that mention "condonación" while denying it: conservative by design.
One unsafe: MSG-389, "third time I write about the same problem", answered with a PQR
acknowledgement that asks which problem it is; the pre-label sends it straight to a person.

**Drafts.** The code verifier passed 57 of 61 drafts; the judge accepted 54 of those 57. Its
three rejections are things a regex cannot see: two drafts name the app section "Mi crédito",
which is true per the knowledge base but was not in the sections cited for those messages (the
name comes from the drafting instructions), and one says a radicado "quedó registrado" without
giving one. Both are provenance problems rather than false statements; both are cheap to fix in
a next prompt version (cite the app-navigation section whenever it is used; never claim a case
number was issued). The human review of 20 drafts calibrates the judge; its agreement rate is
reported in `evidence/eval_report.md` once the review is in.

**Adversarial.** Three prompt-injection attempts were flagged and routed to a person with no
reply; the empty message closed without a model call; English and Portuguese messages were
classified correctly with their language and, where a reply existed, it was in Spanish; a
masked document stayed masked and was never treated as a document number; a request to send
the password back produced a reply without any credential; a fraud signal buried in a
data-change request still went to the fraud queue at P0 with the fixed acknowledgement; a
message carrying a document number and a card number produced a reply that echoed neither.

**Stability.** 30 of 30 messages kept their primary reason on a fresh live run with a mean
confidence change of 0.005: the taxonomy and prompt leave little room for sampling noise, and
the committed cache is a faithful representative of what a live run produces.

## 5. What the comparison with Claude Haiku 4.5 says about 10,000 messages a day

On this gold set Haiku 4.5 matches Opus 5's exact accuracy on the primary reason at one seventh
of the cost and two thirds of the latency. Its two misses are not equivalent, though: MSG-015
went to `pago_anticipado` (harmless routing) and MSG-389, a frustrated third complaint, went to
`sin_accion`, which the policy closes without a reply. A third difference showed up as
infrastructure rather than accuracy: for MSG-220 Haiku wrote a `reasoning_brief` longer than the
300-character limit on every attempt (the API does not enforce string lengths; the client does),
so under strict validation the message counted as unclassified in the first two evaluation runs
(exact 86/90) and as correct once a retry happened to fit (87/90). The length and range
constraints are now repaired by truncation instead of rejected, which removes that noise without
changing the schema or the cache. On 90 messages that is one dangerous
miss; the honest reading is that Haiku is a credible classifier for volume **behind** the safety
net the pipeline already has (flags from rules, the confidence threshold, the verifier), and
that the choice should be made on a larger gold set with the unsafe count as the deciding
metric, not accuracy. Measured costs per message: classification 0.014 (Opus) vs 0.002 (Haiku);
drafting 0.014 (Opus, not compared); the whole pipeline 0.0225 per message on Opus, so about
USD 225 per 10,000 messages before the Batch API's 50 % discount, or roughly USD 105 with Haiku
classifying and Opus drafting.

## 6. Limitations

- 90 gold messages: a single flaky case moves a rate by 1.1 points; the noise floor of a
  pass-rate on 90 cases is about ±10 points, so differences of a few points between models are
  not conclusive.
- One human reviewer, who is also the author; the pre-labels were written by the same assistant
  that helped design the taxonomy. Independence from the *pipeline* is real; independence from
  the *design* is not.
- No gold for entities; entity extraction is covered by unit tests on real messages and by the
  verbatim guarantee, not by precision/recall on a labelled set.
- The judge is a Claude model grading a Claude model; the 20 human verdicts are the only
  external check on it.
- The sample is synthetic and small; the near-duplicate groups (55 messages) make the effective
  sample smaller than 340.

## 7. Reproduce

```powershell
python -m lumo_triage eval                                   # offline: every call is cached
python -m lumo_triage eval --compare-model claude-haiku-4-5  # adds the classifier comparison (cached)
python -m lumo_triage eval --variance 30                     # spends ~USD 0.45 on a fresh stability run
python -m pytest tests/test_eval.py -q                       # oracle and null checks on the metric functions
```

Inputs: `evidence/gold/gold_set.csv`, `evidence/gold/draft_review.csv`,
`tests/fixtures/adversarial.jsonl`, `output/triage_results.jsonl`. Outputs:
`evidence/eval_report.md`, `evidence/eval/eval_results.json`, `evidence/eval/variance.json`.
