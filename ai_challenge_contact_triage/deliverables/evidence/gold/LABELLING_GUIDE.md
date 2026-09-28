# Gold-set labelling guide

The reference labels of the evaluation are the assistant's pre-labels confirmed or corrected
by a person. This is the protocol the reviewer follows and the vocabulary the CSV accepts.

## Commands

```powershell
python scripts/review_gold.py             # 90 messages: reason, priority, action
python scripts/review_gold.py --drafts    # 20 drafts: could an agent send it as is?
python -m lumo_triage eval --compare-model claude-haiku-4-5   # afterwards; replays from cache
```

Answers inside the reviewer (gold set): `Enter` = agree · `r=<reason>` · `p=<P0..P4>` ·
`a=<action>` · `s=<reason,reason>` (secondary) · `n=<note>` · several at once
(`r=queja_reclamo p=P1 n=formal complaint`) · `?` = list values · `b` = back · `q` = save and quit.
Answers inside the reviewer (drafts): `Enter` = ok · `x=<issue> [note]` = not ok, issue one of
`grounding`, `wrong_answer`, `promise`, `tone`, `incomplete`, `other`.

## How to decide

- **Primary reason** = the request that decides who handles the message. Two requests: the one
  that opens a case, or the one the customer wrote first; the other goes to `s=`.
- **Priority** follows the harm if nobody acts in time, not the customer's tone.
- **Action** follows the policy: can the knowledge base answer it, and does anyone need to act?

## Reasons (25)

| id | means |
|---|---|
| `consulta_saldo_cuotas` | how much do I owe, installments left, next installment value |
| `fecha_de_pago` | when is it due, change the payment date |
| `no_puede_pagar` | cannot pay this month, partial payment, hardship |
| `refinanciacion_acuerdo` | wants a payment agreement or refinancing |
| `pago_no_aplicado` | paid and it is still pending, double charge |
| `metodos_de_pago` | how and where to pay |
| `mora_intereses` | late interest, grace days, what if I pay late |
| `reporte_centrales` | credit-bureau report: when it updates, reported by mistake |
| `cuenta_y_app` | OTP not arriving, blocked account, app failing, password |
| `datos_personales` | change phone, e-mail, other data |
| `certificados_extractos` | paz y salvo, statement, interest certificate |
| `fraude_seguridad` | unrecognised charge, phishing, lost or stolen phone |
| `queja_reclamo` | formal complaint, PQR, bad service |
| `felicitacion_feedback` | thanks or praise for a person or the product |
| `cancelacion` | close the credit or the account |
| `hablar_con_humano` | wants a person and asks nothing else |
| `fuera_de_alcance` | not about Lumo, or a product Lumo does not sell |
| `intereses_y_cargos` | regular rate, fees, insurance, "why did it go up" (not late interest) |
| `pago_anticipado` | pay ahead, settle early, discount for prepaying |
| `estado_solicitud` | status of a credit application |
| `informacion_general` | hours, phone line, offices |
| `privacidad_habeas_data` | what data do you hold, delete my data, stop the offers |
| `saludo_incompleto` | just "hola" |
| `sin_accion` | "ok gracias", "ya quedó resuelto" |
| `ruido` | gibberish, tests, punctuation |

## Priorities

| level | SLA | use it when |
|---|---|---|
| P0 | 1 h | active security or fraud risk (lost phone, unrecognised charge, phishing with a real account at stake) |
| P1 | 4 h | money wrongly taken, legal exposure, imminent bureau reporting, vulnerable customer (job loss, illness) |
| P2 | 24 h | cannot pay or use the product, formal complaints, hardship without vulnerability |
| P3 | 48 h | information, certificates, data updates |
| P4 | none | courtesy, noise, nothing to do |

## Actions

| action | meaning |
|---|---|
| `auto_reply` | the knowledge base answers it and nobody needs to act; the draft is sent |
| `auto_reply_and_route` | the draft is sent as an acknowledgement and a case is opened for a team |
| `route_to_human` | no automatic reply; a person answers (no policy, wants a person, unclear) |
| `close_no_reply` | noise or a closing message; nothing to answer |

## Draft verdicts

`ok` = an agent could send it as is. `not_ok` when it states something the cited policy does not
support (`grounding`), answers the wrong question (`wrong_answer`), promises a refund, forgiveness,
deletion of history or an amount (`promise`), reads cold, blaming or too long (`tone`), leaves the
main request unanswered (`incomplete`), or anything else (`other`).
