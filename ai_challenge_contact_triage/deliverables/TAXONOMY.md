# Taxonomy v2 — what changed from the CX team's draft, and why

The CX draft (`../taxonomy.md`) has 17 reasons. Reading all 340 messages showed three kinds of
gaps: messages with no home, reasons that mixed a *topic* with a *signal* (urgency, legal risk,
"I want a human"), and reasons whose handling depends on whether the knowledge base covers them.
Version 2 keeps the 17 reasons, adds 8, and moves 4 signals into cross-cutting flags. The
machine-readable version is `lumo_triage/policy/taxonomy.yaml`; `tests/test_policy_consistency.py`
checks that every reason has valid defaults, cites existing KB sections and has real example
messages.

## 1. Design rules

1. **A reason is a topic, not an urgency.** Urgency, legal exposure, hardship and "talk to a
   human" are flags that can attach to any reason and change priority and routing.
2. **Every reason declares its knowledge-base coverage** (`full`, `partial`, `none`). Only
   `full` and `partial` reasons may get a model-written draft, and only citing their sections;
   `none` reasons are routed to a person with the gap named. This is how "if the policy doesn't
   cover it, that itself is a signal" becomes code.
3. **Every reason has example message ids** from the sample so the classification can be
   audited against real text.

## 2. Reasons added

| Reason | Why it was missing | Sample messages | KB coverage → handling |
|---|---|---|---|
| `intereses_y_cargos` | The draft only had `mora_intereses` (late interest). Seven messages dispute the *regular* rate, a "cuota de manejo", an unauthorised insurance charge or "why did my installment go up". Under v1 they would be mislabelled as late-interest questions and answered with the grace-period policy, which is wrong. | MSG-007, 029, 281, 296, 341, 387, 388 | none → `pagos_conciliacion`, no draft |
| `pago_anticipado` | Prepaying installments or settling the loan early fell between `consulta_saldo_cuotas` and `cancelacion`, yet the KB answers it precisely (no penalty, interest reduced, detail shown in the app). Separating it turns seven human tickets into safe auto-replies. | MSG-006, 149, 193, 240, 242, 282, 319 | full → auto-reply |
| `estado_solicitud` | "What happened to my credit application" is pre-sale; no v1 reason fits and the KB is silent. | MSG-014 | none → `onboarding` |
| `informacion_general` | Hours, phone line, branches. Lumo-related, so not `fuera_de_alcance`, but the KB has no hours or numbers; a draft would invent them. | MSG-010, 031, 186, 189, 289, 360 | none → `cx_general` |
| `privacidad_habeas_data` | "What data do you hold about me", "delete my data", "stop sending offers". A legal obligation (Ley 1581 de 2012) with its own owner and deadline; it must not be handled as `datos_personales` or `cancelacion`. | MSG-182, 344, 367 | none → `datos_privacidad` |
| `saludo_incompleto` | A bare "hola" is not noise and not out of scope: the right action is to ask what the customer needs, with a fixed template and no model call. | MSG-192, 269, 374 | template |
| `sin_accion` | "ok gracias", "todo bien", "ya quedó resuelto" close a conversation; v1 would have forced them into `felicitacion_feedback`, which routes to a feedback report. | MSG-025, 348, 399 | close, no reply |
| `ruido` | Gibberish and tests ("asdkjas hola", "???", "…"). Separating them from `fuera_de_alcance` keeps the out-of-scope count meaningful and skips the model. | MSG-119, 143, 190, 191, 250, 290, 346, 349, 365 | close, no reply |

## 3. Reasons kept, with a sharpened definition

| Reason | What changed |
|---|---|
| `fuera_de_alcance` | Split by `out_of_scope_kind`: `unrelated` (Rappi, pizzería, weather, trivia, another telco) gets a courtesy template; `other_business_inquiry` (iPhones, car loans, mortgages, insurance, savings) is a sales lead and goes to `comercial` without a draft. |
| `hablar_con_humano` | Kept as a reason only when nothing else is asked. When the customer asks something *and* wants a person, the real topic is the reason and `requests_human` is a flag, so the queue is still the right one. |
| `cuenta_y_app` | The KB covers OTP, blocked accounts and app failures. Twelve messages talk about a "contraseña"; the policy says login is document + OTP and has no password flow. Those are `partial` coverage with an explicit policy gap: the draft may explain the OTP flow but never a password reset. |
| `datos_personales` | Phone and email changes are covered (app, "Mi perfil"); address and any other field are not. The gap is reported and the case routed. |
| `reporte_centrales` | Two situations, one reason: "when is my report updated after paying" is fully answerable (next cycle, up to 30 days, history is never erased); "you reported me by mistake" goes to Cartera/Legal and the draft never confirms an error. |
| `certificados_extractos` | Only the three documents in the policy are offered (paz y salvo / al día, extracto de pagos, certificado de intereses). "Certificado de deuda" and "retención en la fuente" are not in the policy and get an agent. |
| `metodos_de_pago` | Nequi, Daviplata and Baloto appear in the messages but not in the policy; the draft lists the accepted methods and does not confirm the others. |
| `no_puede_pagar` vs `refinanciacion_acuerdo` | Kept separate as in v1: the first is a situation, the second a request. Both route to Cartera; the split preserves the CX team's reporting. |

## 4. Signals moved to flags

| Flag | Was implicit in | Effect (see `routing.yaml`) |
|---|---|---|
| `requests_human` | `hablar_con_humano` | route to a person, keep the topic's queue, priority at least P2 |
| `fraud_or_security` | `fraude_seguridad` | P0, fraud queue, fixed safety acknowledgement, whatever the topic |
| `legal_threat`, `collections_harassment` | `queja_reclamo` | P1, `pqr_legal` |
| `vulnerable_customer`, `imminent_deadline`, `repeat_contact` | nowhere | one priority level up each |
| `prompt_injection_suspected` | nowhere | never auto-answered |
| `pii_present` | nowhere | draft must not echo the document number |

## 5. Priority model

`P0` critical (1 h): active security or fraud risk. `P1` high (4 h): money wrongly taken, legal
exposure, imminent reporting, vulnerable customer. `P2` normal (24 h): blocked from paying or
using the product, formal complaints, hardship. `P3` low (48 h): information, documents, data
updates. `P4` none: courtesy or nothing to do. Base priority comes from the reason; flags bump
it; the model never sets it directly.

## 6. What the sample looks like under v2 (rough keyword pass, for orientation only)

The bucketing in `evidence/message_profiling.md` spreads the 340 messages over ~20 buckets with
no bucket above 10 % and 28 messages matching no keyword at all. That flat distribution is the
argument for a model-based classifier with a deterministic layer around it, rather than rules.
The measured distribution, from the pipeline itself, is in `output/batch_summary.md`.
