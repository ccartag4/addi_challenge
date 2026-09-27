# Batch summary — Lumo contact triage

Generated 2026-09-27T21:46:53Z by pipeline `0.4.0 (classify-v1, draft-v2)`, model `claude-opus-5`. Computed from `triage_results.jsonl` (340 messages); nothing in this file was written by the model.

## Headline

| | |
|---|---:|
| Messages | 340 |
| Reply ready to send (auto-answerable) | 278 (81.8 %) |
| of which model drafts that passed the verifier / fixed templates | 234 / 44 |
| Cases opened for a person | 202 (59.4 %) |
| of which answered automatically and routed / needing a person's answer | 152 / 50 |
| Closed without reply (noise, closures) | 12 |
| Model drafts rejected by the verifier | 4 |
| Messages touching a knowledge-base gap | 61 |
| Unclassified | 0 |

## What stands out

- 278 of 340 messages (81.8 %) leave with a reply ready to send; 202 (59.4 %) open a case for a person.
- 22 security or fraud cases (6.5 %) go to the fraud queue at P0 with the fixed safety acknowledgement.
- 19 customers explicitly asked for a person; 13 of them asked nothing else.
- 13 messages mention job loss, illness or a similar hardship and were raised to P1.
- Knowledge-base gaps found while drafting: Certificados y extractos (6); Cuenta y app (6); Métodos de pago (6). The customers' own requests are listed under policy gaps.
- 16 messages fall on reasons the knowledge base does not cover at all (fees and rates, hours, application status, habeas data); they always reach a person.
- 4 model drafts were rejected by the verifier and routed to a person: forbidden_phrases (3), numbers (1).
- 0 classifications fell below the 0.60 confidence threshold; 7 more sit between 0.60 and 0.69 and are worth a spot check.
- 2 exact duplicates reused the original's result; 55 messages sit in 21 near-duplicate groups (largest 5): repeated contacts or templated complaints.
- Busiest day: 2026-05-06 with 50 messages (14.7 %).
- 131 messages (38.5 %) carry negative sentiment.

## Volume by contact reason

| Reason | n | share | reply ready | case opened | mean conf. |
|---|---:|---:|---:|---:|---:|
| `pago_no_aplicado` — Pago no aplicado o doble | 31 | 9.1 % | 29 | 31 | 0.91 |
| `consulta_saldo_cuotas` — Consulta de saldo y cuotas | 26 | 7.6 % | 26 | 1 | 0.90 |
| `certificados_extractos` — Certificados y extractos | 22 | 6.5 % | 20 | 7 | 0.91 |
| `fraude_seguridad` — Fraude y seguridad | 22 | 6.5 % | 22 | 22 | 0.96 |
| `no_puede_pagar` — No puede pagar | 19 | 5.6 % | 18 | 19 | 0.91 |
| `reporte_centrales` — Reporte a centrales de riesgo | 19 | 5.6 % | 19 | 19 | 0.90 |
| `fecha_de_pago` — Fecha de pago | 19 | 5.6 % | 18 | 3 | 0.92 |
| `cuenta_y_app` — Cuenta y app | 18 | 5.3 % | 18 | 6 | 0.93 |
| `metodos_de_pago` — Métodos de pago | 18 | 5.3 % | 18 | 6 | 0.93 |
| `refinanciacion_acuerdo` — Refinanciación o acuerdo de pago | 17 | 5.0 % | 15 | 17 | 0.89 |
| `datos_personales` — Datos personales | 16 | 4.7 % | 13 | 4 | 0.94 |
| `felicitacion_feedback` — Felicitación o feedback positivo | 14 | 4.1 % | 14 | 0 | 0.96 |
| `fuera_de_alcance` — Fuera de alcance | 14 | 4.1 % | 5 | 9 | 0.94 |
| `hablar_con_humano` — Hablar con un humano | 13 | 3.8 % | 0 | 13 | 0.92 |
| `cancelacion` — Cancelación | 13 | 3.8 % | 13 | 13 | 0.90 |
| `queja_reclamo` — Queja o reclamo (PQR) | 12 | 3.5 % | 11 | 12 | 0.85 |
| `mora_intereses` — Mora e intereses de mora | 10 | 2.9 % | 10 | 3 | 0.86 |
| `ruido` — Ruido | 9 | 2.6 % | 0 | 0 | 0.99 |
| `intereses_y_cargos` — Intereses corrientes y cargos | 8 | 2.4 % | 0 | 8 | 0.82 |
| `pago_anticipado` — Pago anticipado o liquidación total | 6 | 1.8 % | 6 | 1 | 0.88 |
| `informacion_general` — Información general de Lumo | 6 | 1.8 % | 0 | 6 | 0.91 |
| `sin_accion` — Cierre o agradecimiento sin solicitud | 3 | 0.9 % | 0 | 0 | 1.00 |
| `saludo_incompleto` — Saludo sin pregunta | 3 | 0.9 % | 3 | 0 | 1.00 |
| `estado_solicitud` — Estado de una solicitud de crédito | 1 | 0.3 % | 0 | 1 | 0.95 |
| `privacidad_habeas_data` — Privacidad y habeas data | 1 | 0.3 % | 0 | 1 | 0.94 |

## Actions, priorities and queues

| Action | n |
|---|---:|
| `auto_reply_and_route` | 152 |
| `auto_reply` | 126 |
| `route_to_human` | 50 |
| `close_no_reply` | 12 |

| Priority | SLA | n | of which cases for a person |
|---|---|---:|---:|
| P0 (critical) | 1 h | 22 | 22 |
| P1 (high) | 4 h | 30 | 29 |
| P2 (normal) | 24 h | 123 | 104 |
| P3 (low) | 48 h | 131 | 47 |
| P4 (none) | - | 34 | 0 |

| Queue | cases | P0 | P1 | P2 | P3 |
|---|---:|---:|---:|---:|---:|
| `cx_general` | 54 | 0 | 0 | 17 | 37 |
| `cartera` | 53 | 0 | 15 | 38 | 0 |
| `pagos_conciliacion` | 39 | 0 | 1 | 38 | 0 |
| `fraude` | 22 | 22 | 0 | 0 | 0 |
| `pqr_legal` | 14 | 0 | 13 | 1 | 0 |
| `comercial` | 9 | 0 | 0 | 0 | 9 |
| `soporte_tecnico` | 6 | 0 | 0 | 6 | 0 |
| `datos_privacidad` | 4 | 0 | 0 | 4 | 0 |
| `onboarding` | 1 | 0 | 0 | 0 | 1 |

## Knowledge-base gaps (the signal the CX team asked for)

| Gap | messages |
|---|---:|
| intereses_y_cargos: no policy | 8 |
| informacion_general: no policy | 6 |
| certificados_extractos: partially covered | 6 |
| cuenta_y_app: partially covered | 6 |
| metodos_de_pago: partially covered | 6 |
| refinanciacion_acuerdo: partially covered | 4 |
| datos_personales: partially covered | 4 |
| pago_no_aplicado: partially covered | 3 |
| fecha_de_pago: partially covered | 3 |
| queja_reclamo: partially covered | 3 |
| cancelacion: partially covered | 3 |
| mora_intereses: partially covered | 3 |
| no_puede_pagar: partially covered | 2 |
| pago_anticipado: partially covered | 1 |
| estado_solicitud: no policy | 1 |
| consulta_saldo_cuotas: partially covered | 1 |
| privacidad_habeas_data: no policy | 1 |

**pago_anticipado** — Pago anticipado o liquidación total

- MSG-006: El paso a paso exacto para registrar el pago anticipado.

**intereses_y_cargos** — Intereses corrientes y cargos

- The knowledge base has no policy on regular interest rates, fees or insurance charges.

**informacion_general** — Información general de Lumo

- The knowledge base has no opening hours, phone lines or office addresses.

**estado_solicitud** — Estado de una solicitud de crédito

- The knowledge base says nothing about credit applications or their status.

**pago_no_aplicado** — Pago no aplicado o doble

- MSG-030: Si el excedente puede abonarse a la próxima cuota.
- MSG-123: El cliente pide que se revise o retire el cobro de intereses de mora, algo que las secciones no contemplan.
- MSG-142: Si el pago adicional queda como saldo a favor o se devuelve; el equipo de Pagos lo confirmará tras la revisión.

**certificados_extractos** — Certificados y extractos

- MSG-132: No hay información sobre la emisión del certificado de retención en la fuente ni sobre si Lumo lo expide.; No se indica cómo ni cuándo el cliente podría obtener ese certificado del año anterior.; Only paz y salvo / al día, the payment statement and the interest certificate exist in the policy; other certificates need an agent.
- MSG-145: Certificado de deuda actual con desglose de capital e intereses causados; Only paz y salvo / al día, the payment statement and the interest certificate exist in the policy; other certificates need an agent.
- MSG-171: El certificado de saldo a la fecha no está contemplado entre los certificados disponibles descritos.; Only paz y salvo / al día, the payment statement and the interest certificate exist in the policy; other certificates need an agent.
- MSG-232: El envío de los documentos al correo electrónico del cliente.
- MSG-262: Si el certificado puede enviarse al correo electrónico del cliente.
- MSG-328: Si el extracto puede enviarse directamente al correo del cliente.

**refinanciacion_acuerdo** — Refinanciación o acuerdo de pago

- MSG-144: La solicitud de reducir o suspender la frecuencia de las llamadas de cobranza no está cubierta por las políticas disponibles.
- MSG-210: Si la deuda puede dividirse en más cuotas y en cuántas
- MSG-321: Los pasos exactos para activar el plan de pagos desde la app.
- MSG-338: Si se permite renegociar un acuerdo de pago por segunda vez y bajo qué condiciones.

**cuenta_y_app** — Cuenta y app

- MSG-146: The policy has no password flow (login is document + OTP); a support case is opened.
- MSG-166: The policy has no password flow (login is document + OTP); a support case is opened.
- MSG-224: The policy has no password flow (login is document + OTP); a support case is opened.
- MSG-260: The policy has no password flow (login is document + OTP); a support case is opened.
- MSG-309: The policy has no password flow (login is document + OTP); a support case is opened.
- MSG-368: The policy has no password flow (login is document + OTP); a support case is opened.

**fecha_de_pago** — Fecha de pago

- MSG-153: Confirmación de la fecha exacta de vencimiento de la cuota del mes para el crédito 8902.; Aclaración sobre la diferencia entre la fecha mostrada en la app y la del mensaje recibido.
- MSG-198: Cuáles canales de pago cobran comisión y cuáles no.
- MSG-380: La fecha exacta de vencimiento de la cuota de mayo del cliente.

**datos_personales** — Datos personales

- MSG-169: Cómo actualizar la dirección de residencia en el perfil; Address changes are not covered by the policy (only phone and e-mail).
- MSG-228: Cómo actualizar la dirección de residencia; Address changes are not covered by the policy (only phone and e-mail).
- MSG-285: Cómo actualizar la dirección de residencia en el sistema de Lumo.; Cómo actualizar la ciudad de residencia en el sistema de Lumo.; Address changes are not covered by the policy (only phone and e-mail).
- MSG-327: Cómo corregir o actualizar la dirección registrada en los datos personales.; Address changes are not covered by the policy (only phone and e-mail).

**queja_reclamo** — Queja o reclamo (PQR)

- MSG-177: La exigencia de detener de inmediato los mensajes de cobranza y las llamadas a familiares.
- MSG-199: El detalle de cómo se calcularon los intereses del crédito 8941.
- MSG-389: El cliente no indica cuál es el problema de fondo, por lo que no se puede dar una solución concreta.

**cancelacion** — Cancelación

- MSG-182: El procedimiento y los tiempos para la eliminación de los datos personales del cliente.
- MSG-315: La solicitud de dejar de recibir mensajes o comunicaciones no está cubierta por las secciones disponibles.
- MSG-367: El procedimiento para dejar de recibir ofertas comerciales no está cubierto por las secciones disponibles.

**no_puede_pagar** — No puede pagar

- MSG-194: El valor exacto del interés de mora si paga la próxima semana, que depende de su cuenta.
- MSG-293: El monto mínimo específico que puede abonar este mes.

**metodos_de_pago** — Métodos de pago

- MSG-216: Si es posible pagar con Nequi.; Payment rails other than PSE, cards, Efecty and bank correspondents (Nequi, Daviplata, Baloto, transfers, payment links) are not in the policy.
- MSG-217: Si es posible pagar en Baloto; Payment rails other than PSE, cards, Efecty and bank correspondents (Nequi, Daviplata, Baloto, transfers, payment links) are not in the policy.
- MSG-323: Payment rails other than PSE, cards, Efecty and bank correspondents (Nequi, Daviplata, Baloto, transfers, payment links) are not in the policy.
- MSG-340: El número de cuenta bancaria para hacer transferencia.; El link de pago solicitado.; Payment rails other than PSE, cards, Efecty and bank correspondents (Nequi, Daviplata, Baloto, transfers, payment links) are not in the policy.
- MSG-352: La ruta exacta dentro de la app para llegar a la opción de pago con PSE.
- MSG-376: Si se puede pagar en Baloto.; Payment rails other than PSE, cards, Efecty and bank correspondents (Nequi, Daviplata, Baloto, transfers, payment links) are not in the policy.

**mora_intereses** — Mora e intereses de mora

- MSG-219: El valor o porcentaje exacto del interés diario de mora.
- MSG-258: El desglose exacto de la diferencia entre $120.000 y $138.500 en su cuota.
- MSG-272: El valor exacto de los intereses de mora de su cuota no se puede calcular por este canal.

**consulta_saldo_cuotas** — Consulta de saldo y cuotas

- MSG-248: Si se puede pagar a través de Nequi y cómo hacerlo.

**privacidad_habeas_data** — Privacidad y habeas data

- The knowledge base has no habeas-data procedure (data access, deletion, marketing opt-out).

## Verifier rejections

| id | reason | failed check | draft (kept for the agent, not sent) |
|---|---|---|---|
| MSG-020 | `refinanciacion_acuerdo` | forbidden_phrases: FAIL ['condonaci'] | ¡Hola! Gracias por escribirnos y contarnos tu situación. Sí, cuando no puedes pagar existe la opción de un acuerdo de pago o refinanciación. Ya estamos escaland… |
| MSG-039 | `certificados_extractos` | numbers: FAIL not in cited sections or message: ['2026'] | ¡Hola! Claro que sí, con gusto te oriento.  El certificado de intereses pagados lo puedes solicitar en la app, en la sección "Documentos", o con un asesor. La g… |
| MSG-274 | `refinanciacion_acuerdo` | forbidden_phrases: FAIL ['condonaci'] | Hola, gracias por escribirnos y contarnos tu situación. Sí, podemos buscar un acuerdo de pago: esta opción la gestiona el equipo de Cartera, así que remitimos t… |
| MSG-394 | `no_puede_pagar` | forbidden_phrases: FAIL ['condonaci'] | Hola, lamento que este mes se te haya complicado. Podemos buscar una salida: tienes la opción de un acuerdo de pago o refinanciación, y ya estamos escalando tu … |

## Flags

| Flag | n |
|---|---:|
| `fraud_or_security` | 22 |
| `requests_human` | 19 |
| `vulnerable_customer` | 13 |
| `repeat_contact` | 10 |
| `imminent_deadline` | 4 |
| `collections_harassment` | 3 |
| `pii_present` | 2 |
| `legal_threat` | 1 |

## Duplicates and low confidence

Exact duplicates reused: 2. Near-duplicate messages: 55 in 21 groups (largest 5). Classifications below the routing threshold: 0.

| id | conf. | reason | summary |
|---|---:|---|---|
| MSG-220 | 0.60 | `intereses_y_cargos` | El cliente no entiende un cobro adicional que le llegó y pregunta si corresponde a intereses de mora. |
| MSG-040 | 0.62 | `hablar_con_humano` | El cliente lleva 20 minutos esperando y pregunta si hay alguien que lo atienda. |
| MSG-176 | 0.62 | `pago_no_aplicado` | Cliente molesto reporta un doble cobro de la misma cuota sin devolución del dinero y pide radicar un reclamo formal. |
| MSG-194 | 0.62 | `no_puede_pagar` | El cliente no puede pagar este mes y pregunta cuánto sería el interés de mora si paga la próxima semana y si lo reportarían a centrales. |
| MSG-389 | 0.62 | `queja_reclamo` | El cliente se queja de que es la tercera vez que escribe por el mismo problema y aún no se lo resuelven. |
| MSG-249 | 0.68 | `certificados_extractos` | El cliente pide su extracto del mes y consultar si ya se aplicó un pago hecho la semana pasada que la app aún muestra pendiente. |
| MSG-298 | 0.68 | `consulta_saldo_cuotas` | El cliente pide conocer su saldo, avisa que no puede pagar la totalidad este mes y quiere cambiar la fecha de pago. |

## Channels

chat: 119, whatsapp: 115, email: 106.

## Model usage and cost

| | |
|---|---:|
| Live model calls in this run | 0 |
| Responses replayed from cache in this run | 568 |
| Prompt tokens: uncached / cache read / cache write | 161,328 / 2,798,776 / 31,419 |
| Output tokens (JSON plus thinking) | 213,301 |
| Cost of the calls behind this output | USD 7.73 (≈ USD 0.0227 per message) |
| Spent by this run | USD 0.00 |

Reproduce: `./run.ps1` or `./run.sh` from `deliverables/` (offline from the committed cache without a key; live with `ANTHROPIC_API_KEY`).
