# Message profiling — data/messages.jsonl

Generated 2026-09-27 15:00 by `scripts/profile_messages.py`. 340 messages.

## Shape

| Measure | Value |
|---|---|
| Channels | {'whatsapp': 115, 'chat': 119, 'email': 106} |
| Timestamp shapes | {'9999-99-99T99:99:99': 40, '9999-99-99T99:99:99-99:99': 300} |
| Date range | 2026-05-04 .. 2026-05-15 |
| Sender shapes | {'phone': 115, 'client_id': 119, 'email': 106} |
| Text length min / median / p90 / max | 3 / 88 / 140 / 247 |
| Exact duplicate texts (normalised, non-empty) | 2 in 2 groups |
| Near-duplicate pairs (token Jaccard >= 0.6) | 40 pairs, 55 (16 %) messages involved |

## Signals (regex over the raw text; a message can hit several)

| Signal | Messages | Example |
|---|---:|---|
| credit number mentioned | 14 (4 %) | MSG-003 |
| document number mentioned | 7 (2 %) | MSG-027 |
| masked identifier (xx / XXX) | 2 (1 %) | MSG-276 |
| amount mentioned | 8 (2 %) | MSG-113 |
| transaction / reference mentioned | 4 (1 %) | MSG-214 |
| explicit date mentioned | 27 (8 %) | MSG-003 |
| bank / payment rail named | 27 (8 %) | MSG-003 |
| multi-intent markers | 16 (5 %) | MSG-011 |
| urgency words | 22 (6 %) | MSG-005 |
| fraud / security signals | 23 (7 %) | MSG-016 |
| legal / regulatory threat or harassment | 3 (1 %) | MSG-177 |
| hardship / vulnerability | 22 (6 %) | MSG-001 |
| asks for a human | 15 (4 %) | MSG-026 |
| out of scope / other business | 28 (8 %) | MSG-008 |
| credit-bureau terms | 31 (9 %) | MSG-005 |
| certificates / statements | 26 (8 %) | MSG-009 |
| password mentioned (KB: login is document + OTP) | 12 (4 %) | MSG-016 |
| address change (not in KB) | 4 (1 %) | MSG-169 |
| application status (not in taxonomy) | 1 (0 %) | MSG-014 |
| interest / fee dispute (not in taxonomy) | 7 (2 %) | MSG-007 |
| prepayment / early settlement (not in taxonomy) | 7 (2 %) | MSG-006 |
| greeting / thanks only or gibberish | 17 (5 %) | MSG-025 |
| mojibake (encoding) | 0 (0 %) | - |
| ALL-CAPS heavy | 1 (0 %) | MSG-312 |

## Rough keyword bucketing (planning aid only, first match wins)

| Bucket | Messages |
|---|---:|
| reporte_centrales | 28 |
| cuenta_y_app | 26 |
| (no keyword match) | 24 |
| fecha_de_pago | 23 |
| fraude_seguridad | 23 |
| refinanciacion_acuerdo | 21 |
| metodos_de_pago | 21 |
| mora_intereses | 18 |
| datos_personales | 16 |
| certificados_extractos | 16 |
| queja_reclamo | 15 |
| consulta_saldo_cuotas | 15 |
| no_puede_pagar | 14 |
| hablar_con_humano | 14 |
| felicitacion_feedback | 13 |
| fuera_de_alcance | 13 |
| cancelacion | 12 |
| pago_no_aplicado | 10 |
| intereses_y_cargos | 8 |
| pago_anticipado | 6 |
| informacion_general | 4 |

Unmatched sample (why rules alone cannot classify):

- MSG-014: buenas quiero saber el estado de mi solicitud de credito que mande hac
- MSG-035: me podrian confirmar a que correo les puedo enviar el comprobante de p
- MSG-119: asdkjas hola
- MSG-143: ...
- MSG-184: quiero hablar con una persona de verdad no con el bot porfavor
- MSG-190: asdkjasd hola?? probando
- MSG-191: ?????
- MSG-192: hola
- MSG-215: Realice el pago de mi cuota el 05 de mayo y aun no se ve reflejado en 
- MSG-241: como cancelo mi cuenta? ya no quiero seguir con el servicio y quiero c
- MSG-250: asdkjasd hola?? prueba prueba
- MSG-269: hola
