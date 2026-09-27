"""
Knowledge-base loader and routing engine. Pure code, no API key: every case constructs a
Classification and checks (priority, action, queue, codes, drafting directives).
"""
from __future__ import annotations

import pytest

from lumo_triage import routing
from lumo_triage.kb import KnowledgeBase, load_kb, split_sections
from lumo_triage.schema import TAXONOMY, Classification, Entities, Flags


def cls(primary, secondary=(), confidence=0.9, oos=None, **flags) -> Classification:
    return Classification(primary_reason=primary, secondary_reasons=list(secondary), confidence=confidence,
                          out_of_scope_kind=oos, flags=Flags(**flags), entities=Entities(), sentiment="neutral",
                          language="es", summary="resumen", reasoning_brief="motivo")


# ---------------------------------------------------------------- knowledge base
def test_kb_loads_every_section_declared_in_the_taxonomy():
    kb = load_kb()
    assert set(kb.sections) == set(TAXONOMY["kb_sections"])
    for s in kb.sections.values():
        assert s.text and s.text.lstrip().startswith("-"), s.id       # bullets under each heading
    assert "5 días calendario" in kb.sections["mora_y_centrales.mora_e_intereses"].text
    assert kb.sections["mora_y_centrales.mora_e_intereses"].digits == {"5"}
    assert "24" in kb.sections["pagos_y_cuotas.pagos_no_aplicados"].digits


def test_kb_sections_for_reasons_is_an_ordered_union():
    kb = load_kb()
    ids = kb.section_ids_for(["reporte_centrales", "certificados_extractos"])
    assert ids == ["mora_y_centrales.reporte_centrales", "mora_y_centrales.paz_y_salvo", "datos_certificados_pqr.certificados_extractos"]
    rendered = KnowledgeBase.render(kb.get(ids))
    assert rendered.count("<kb_section ") == 3 and 'id="mora_y_centrales.paz_y_salvo"' in rendered


def test_split_sections_keeps_only_level_two_headings():
    md = "# Title\nintro\n## A\n- a1\n- a2\n## B\n- b1\n"
    assert split_sections(md) == {"A": "- a1\n- a2", "B": "- b1"}


# ---------------------------------------------------------------- routing: defaults and overrides
def test_plain_reason_uses_its_defaults_and_allows_a_draft():
    plan = routing.route(cls("metodos_de_pago"))
    d = plan.decision
    assert (d.priority, d.sla_hours, d.action, d.queue) == ("P3", 48, "auto_reply", "none")
    assert d.policy_coverage == "full" and d.policy_gap is None and d.reason_codes == []
    assert plan.draft_allowed and plan.reply_source == "llm" and plan.allowed_sections == ["pagos_y_cuotas.metodos_de_pago"]
    app = routing.route(cls("cuenta_y_app"))
    assert app.decision.action == "auto_reply" and app.decision.queue == "none"     # default_queue only when a person is involved
    assert routing.route(cls("cuenta_y_app", requests_human=True)).decision.queue == "soporte_tecnico"


def test_fraud_flag_wins_over_everything():
    plan = routing.route(cls("consulta_saldo_cuotas", fraud_or_security=True, requests_human=True))
    d = plan.decision
    assert d.action == "auto_reply_and_route" and d.queue == "fraude" and d.priority == "P0" and d.sla_hours == 1
    assert d.reason_codes[0] == "OVR_FRAUD" and plan.template == "security_ack" and not plan.draft_allowed


def test_requests_human_routes_to_the_reason_queue_without_a_draft():
    plan = routing.route(cls("pago_no_aplicado", requests_human=True))
    d = plan.decision
    assert d.action == "route_to_human" and d.queue == "pagos_conciliacion" and d.priority == "P2"
    assert "OVR_HUMAN" in d.reason_codes and not plan.draft_allowed and plan.reply_source == "none"
    plan = routing.route(cls("metodos_de_pago", requests_human=True))
    assert plan.decision.queue == "cx_general"                       # reason has no queue of its own


def test_legal_flags_go_to_pqr_legal_with_the_pqr_section_added():
    plan = routing.route(cls("refinanciacion_acuerdo", collections_harassment=True))
    d = plan.decision
    assert d.action == "auto_reply_and_route" and d.queue == "pqr_legal" and d.priority == "P1"
    assert plan.draft_allowed and plan.allowed_sections[-1] == "datos_certificados_pqr.pqr"


def test_low_confidence_goes_to_a_person():
    plan = routing.route(cls("fecha_de_pago", confidence=0.55))
    assert plan.decision.action == "route_to_human" and plan.decision.queue == "cx_general"
    assert "OVR_LOW_CONFIDENCE" in plan.decision.reason_codes and not plan.draft_allowed
    assert routing.route(cls("fecha_de_pago", confidence=0.60)).draft_allowed   # threshold is exclusive


def test_no_policy_means_a_named_gap_and_a_person():
    plan = routing.route(cls("informacion_general"))
    d = plan.decision
    assert d.action == "route_to_human" and d.queue == "cx_general" and d.priority == "P3"
    assert d.policy_coverage == "none" and "opening hours" in d.policy_gap and "OVR_NO_POLICY" in d.reason_codes


def test_out_of_scope_kinds_are_handled_differently():
    unrelated = routing.route(cls("fuera_de_alcance", oos="unrelated"))
    assert unrelated.template == "unrelated" and unrelated.decision.action == "auto_reply" and unrelated.decision.priority == "P4"
    sales = routing.route(cls("fuera_de_alcance", oos="other_business_inquiry"))
    assert sales.decision.action == "route_to_human" and sales.decision.queue == "comercial" and sales.template is None


def test_habeas_data_as_secondary_reason_reaches_the_privacy_owner():
    plan = routing.route(cls("cancelacion", secondary=["privacidad_habeas_data"]))
    d = plan.decision
    assert "OVR_HABEAS" in d.reason_codes and d.queue == "datos_privacidad" and d.action == "auto_reply_and_route"
    assert d.priority == "P2" and plan.draft_allowed                # cancellation steps can still be drafted
    primary = routing.route(cls("privacidad_habeas_data"))
    assert primary.decision.action == "route_to_human" and primary.decision.queue == "datos_privacidad"
    assert "NO_REPLY_SOURCE" in primary.decision.reason_codes and primary.decision.policy_gap


# ---------------------------------------------------------------- routing: priority arithmetic
@pytest.mark.parametrize("primary, secondary, flags, expected, code", [
    ("no_puede_pagar", [], {"vulnerable_customer": True}, "P1", "BUMP_VULNERABLE_CUSTOMER"),
    ("consulta_saldo_cuotas", [], {"vulnerable_customer": True}, "P1", "BUMP_VULNERABLE_CUSTOMER"),   # floor P1
    ("mora_intereses", [], {"imminent_deadline": True}, "P2", "BUMP_IMMINENT_DEADLINE"),
    ("queja_reclamo", [], {"repeat_contact": True}, "P1", "BUMP_REPEAT_CONTACT"),
    ("consulta_saldo_cuotas", ["no_puede_pagar"], {}, "P2", "PRIO_SECONDARY_NO_PUEDE_PAGAR"),
    ("fraude_seguridad", [], {"fraud_or_security": True, "repeat_contact": True}, "P0", "OVR_FRAUD"),  # never past P0
])
def test_priority_arithmetic(primary, secondary, flags, expected, code):
    plan = routing.route(cls(primary, secondary=secondary, **flags))
    assert plan.decision.priority == expected, plan.decision
    assert code in plan.decision.reason_codes


def test_tier0_and_template_reasons():
    ruido = routing.route(cls("ruido", confidence=1.0))
    assert (ruido.decision.action, ruido.decision.queue, ruido.decision.priority, ruido.decision.sla_hours) == ("close_no_reply", "none", "P4", None)
    greeting = routing.route(cls("saludo_incompleto", confidence=1.0))
    assert greeting.template == "greeting_prompt" and greeting.decision.action == "auto_reply"
    thanks = routing.route(cls("felicitacion_feedback"))
    assert thanks.template == "feedback_thanks" and thanks.reply_source == "template"


def test_wanting_a_person_and_being_off_topic_are_not_policy_gaps():
    assert routing.route(cls("hablar_con_humano", requests_human=True)).decision.policy_gap is None
    assert routing.route(cls("fuera_de_alcance", oos="unrelated")).decision.policy_gap is None
    assert routing.route(cls("intereses_y_cargos")).decision.policy_gap.startswith("The knowledge base has no policy")


def test_known_policy_gaps_are_detected_by_pattern():
    assert routing.known_gaps("cuenta_y_app", "no puedo entrar me dice contraseña incorrecta")
    assert routing.known_gaps("cuenta_y_app", "no me llega el codigo de verificacion") == []
    assert routing.known_gaps("metodos_de_pago", "puedo pagar por Nequi?") and routing.known_gaps("metodos_de_pago", "puedo pagar en efecty?") == []
    assert routing.known_gaps("datos_personales", "quiero cambiar mi direccion de residencia")
    assert routing.known_gaps("certificados_extractos", "necesito el certificado de retencion en la fuente")
    assert routing.known_gaps("pago_no_aplicado", "contraseña") == []          # patterns are bound to their reason
    for reason, items in routing.KNOWN_GAPS.items():
        for pattern, gap in items:
            assert gap.endswith(".") and pattern.pattern, reason


def test_missing_classification_is_routed_to_a_person():
    plan = routing.route(None)
    d = plan.decision
    assert d.action == "route_to_human" and d.queue == "cx_general" and d.priority == "P3"
    assert d.reason_codes == ["LLM_UNAVAILABLE"] and not plan.draft_allowed


def test_every_reason_routes_without_error_and_auto_actions_have_a_reply_source():
    for r in TAXONOMY["reasons"]:
        plan = routing.route(cls(r["id"], oos="unrelated" if r["id"] == "fuera_de_alcance" else None))
        if plan.decision.action in routing.AUTO_ACTIONS:
            assert plan.draft_allowed or plan.template, r["id"]
        if plan.decision.action == "route_to_human":
            assert plan.decision.queue != "none", r["id"]
