"""
Verifier, drafting prompt and end-to-end record assembly with a fake SDK client. No API key.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumo_triage import classify, draft, normalize, pipeline, routing
from lumo_triage.kb import load_kb
from lumo_triage.llm import LLMClient, LLMConfig
from lumo_triage.routing import ROUTING
from lumo_triage.schema import Classification, Entities, Flags
from lumo_triage.verify import DraftCheckInput, failed_checks, verify

DATA = Path(__file__).resolve().parents[1].parent / "data" / "messages.jsonl"
RULES = ROUTING["verifier"]


@pytest.fixture(scope="module")
def kb():
    return load_kb()


@pytest.fixture(scope="module")
def by_id():
    return {m.id: m for m in normalize.prepare(DATA)}


def check(kb, text, citations, allowed=None, message="pague ayer por pse y no se refleja, credito 4471", entities=None, source="llm"):
    return verify(DraftCheckInput(text, citations, allowed if allowed is not None else citations, kb, message,
                                  entities or Entities(), source=source, rules=RULES))


GOOD = ("¡Hola! Gracias por escribirnos. Si tu pago por PSE no se refleja en 24 horas, envíanos el comprobante y "
        "abrimos un caso de conciliación; el equipo de Pagos lo revisa en hasta 5 días hábiles. Estamos escalando tu "
        "caso al equipo de Pagos. Quedamos atentos por este canal.")


# ---------------------------------------------------------------- verifier
def test_good_draft_passes_every_check(kb):
    result = check(kb, GOOD, ["pagos_y_cuotas.pagos_no_aplicados"])
    assert result.passed, result.checks
    assert all(c.endswith(": ok") for c in result.checks) and len(result.checks) == 8


def test_numbers_must_come_from_cited_sections_or_the_message(kb):
    bad = GOOD.replace("5 días hábiles", "3 días hábiles")
    assert failed_checks(check(kb, bad, ["pagos_y_cuotas.pagos_no_aplicados"])) == ["numbers"]
    words = GOOD.replace("5 días hábiles", "quince días hábiles")
    assert failed_checks(check(kb, words, ["pagos_y_cuotas.pagos_no_aplicados"])) == ["numbers"]
    with_credit = GOOD + " Tu crédito 4471 queda en revisión."           # number from the customer's message
    assert check(kb, with_credit, ["pagos_y_cuotas.pagos_no_aplicados"]).passed


def test_number_words_and_ordinals_from_the_customer_are_allowed(kb):
    twice = GOOD + " Entendemos que hiciste el pago dos veces."
    assert "numbers" in failed_checks(check(kb, twice, ["pagos_y_cuotas.pagos_no_aplicados"]))
    assert check(kb, twice, ["pagos_y_cuotas.pagos_no_aplicados"], message="pague la cuota dos veces por error").passed
    third = GOOD + " Lamento que hayas escrito tres veces por lo mismo."
    assert check(kb, third, ["pagos_y_cuotas.pagos_no_aplicados"], message="esta es la tercera vez que escribo").passed
    derived = GOOD + " Podrás pedirlo a partir de marzo de 2026."          # arithmetic on a year is not in any text
    assert "numbers" in failed_checks(check(kb, derived, ["pagos_y_cuotas.pagos_no_aplicados"], message="intereses pagados en el 2025"))
    idiom = GOOD + " El interés se causa desde el primer día."             # "primer día" is not a figure (MSG-219)
    assert check(kb, idiom, ["pagos_y_cuotas.pagos_no_aplicados"]).passed


def test_spanish_todo_is_not_a_placeholder(kb):
    fine = GOOD + " Ahí queda todo actualizado en un solo lugar."
    assert check(kb, fine, ["pagos_y_cuotas.pagos_no_aplicados"]).passed
    leftover = GOOD + " TODO confirmar el plazo."
    assert "no_placeholders" in failed_checks(check(kb, leftover, ["pagos_y_cuotas.pagos_no_aplicados"]))


def test_citations_must_exist_and_be_allowed(kb):
    assert failed_checks(check(kb, GOOD, [])) == ["citations", "numbers"]   # nothing cited, so the figures are ungrounded too
    assert "citations" in failed_checks(check(kb, GOOD, ["pagos_y_cuotas.pagos_no_aplicados"], allowed=["pagos_y_cuotas.saldo_y_cuotas"]))
    assert "citations" in failed_checks(check(kb, GOOD, ["no.such.section"]))


def test_forbidden_promises_and_credential_requests_fail(kb):
    refund = GOOD + " Te devolvemos el dinero mañana."
    assert failed_checks(check(kb, refund, ["pagos_y_cuotas.pagos_no_aplicados"])) == ["forbidden_phrases"]
    condone = GOOD + " Haremos la condonación de intereses."
    assert "forbidden_phrases" in failed_checks(check(kb, condone, ["pagos_y_cuotas.pagos_no_aplicados"]))
    creds = GOOD + " Envíanos tu contraseña para revisar."
    assert "forbidden_phrases" in failed_checks(check(kb, creds, ["pagos_y_cuotas.pagos_no_aplicados"]))


def test_document_number_is_never_echoed(kb):
    ents = Entities(document_number="9000000003")
    text = GOOD + " Documento 9000000003 verificado."
    r = check(kb, text, ["pagos_y_cuotas.pagos_no_aplicados"], message="mi documento es 9000000003", entities=ents)
    assert "no_document_echo" in failed_checks(r)


def test_length_language_placeholders_and_contacts(kb):
    long_text = GOOD + " palabra" * 160
    assert "length" in failed_checks(check(kb, long_text, ["pagos_y_cuotas.pagos_no_aplicados"]))
    assert "length" in failed_checks(check(kb, "Hola gracias.", ["pagos_y_cuotas.pagos_no_aplicados"]))
    english = "Hello! Thanks for your message, we will review the payment with the team and reply soon."
    assert "language" in failed_checks(check(kb, english, ["pagos_y_cuotas.pagos_no_aplicados"]))
    placeholder = GOOD + " Saludos, [nombre]."
    assert "no_placeholders" in failed_checks(check(kb, placeholder, ["pagos_y_cuotas.pagos_no_aplicados"]))
    contact_ok = GOOD.replace("envíanos el comprobante", "envía el comprobante a pagos@lumo.example")
    assert check(kb, contact_ok, ["pagos_y_cuotas.metodos_de_pago", "pagos_y_cuotas.pagos_no_aplicados"]).passed
    contact_bad = GOOD.replace("envíanos el comprobante", "escribe a soporte@lumo.example")
    assert "contact_details" in failed_checks(check(kb, contact_bad, ["pagos_y_cuotas.pagos_no_aplicados"]))


def test_templates_pass_the_verifier(kb):
    for name, text in ROUTING["templates"].items():
        citations = ROUTING["template_citations"].get(name, [])
        r = check(kb, text.strip(), citations, source="template", message="hola")
        assert r.passed, (name, r.checks)


# ---------------------------------------------------------------- drafting prompt
def test_draft_prompt_is_static_and_user_turn_carries_only_allowed_sections(kb, by_id):
    assert draft.build_draft_system_prompt() == draft.DRAFT_SYSTEM_PROMPT
    assert "MSG-" not in draft.DRAFT_SYSTEM_PROMPT and "<kb_section id=" not in draft.DRAFT_SYSTEM_PROMPT   # no rendered policy text
    m = by_id["MSG-003"]
    c = Classification(primary_reason="pago_no_aplicado", confidence=0.95, flags=Flags(), entities=Entities(credit_number="4471"),
                       sentiment="negative", summary="Pago no reflejado.", reasoning_brief="x")
    plan = routing.route(c)
    content = draft.build_draft_user_content(m, c, plan, kb.get(plan.allowed_sections))
    assert content.count("<kb_section ") == 1 and 'id="pagos_y_cuotas.pagos_no_aplicados"' in content
    assert "case_opened: yes, with el equipo de Pagos" in content and "credit_number" in content and m.text in content
    plan2 = routing.route(Classification(primary_reason="metodos_de_pago", confidence=0.95, flags=Flags(), entities=Entities(),
                                         sentiment="neutral", summary="s", reasoning_brief="x"))
    content2 = draft.build_draft_user_content(m, c, plan2, kb.get(plan2.allowed_sections))
    assert "case_opened: no" in content2


def test_draft_output_schema_has_no_unsupported_keywords():
    from lumo_triage.llm import json_schema_for
    schema = json_schema_for(draft.DraftOutput)
    assert schema["additionalProperties"] is False and set(schema["required"]) >= {"can_answer", "reasoning_brief"}

    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield k
                yield from keys(v)
        elif isinstance(node, list):
            for v in node:
                yield from keys(v)

    assert "maxLength" not in set(keys(schema))          # moved into the description by the SDK, not sent as a keyword


# ---------------------------------------------------------------- end to end with fakes
class FakeResponse:
    def __init__(self, body):
        self._body, self._request_id = body, "req_fake"

    def to_dict(self):
        return self._body


class FakeClient:
    def __init__(self, bodies):
        self.bodies, self.calls = list(bodies), []
        self.beta = self
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.bodies.pop(0))


def body(text):
    return {"model": "claude-opus-5", "stop_reason": "end_turn", "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": 100, "output_tokens": 80, "cache_read_input_tokens": 2000, "cache_creation_input_tokens": 0}}


def classification_json(**over):
    base = dict(primary_reason="pago_no_aplicado", secondary_reasons=[], confidence=0.95, out_of_scope_kind=None, flags=Flags(),
                entities=Entities(), sentiment="negative", language="es", summary="Pago no reflejado.", reasoning_brief="x")
    base.update(over)
    return Classification(**base).model_dump_json()


def draft_json(text=GOOD, can_answer=True, citations=("pagos_y_cuotas.pagos_no_aplicados",), uncovered=()):
    return draft.DraftOutput(can_answer=can_answer, reply_text=text if can_answer else None, citations=list(citations),
                             uncovered_points=list(uncovered), reasoning_brief="ok").model_dump_json()


def make_llm(tmp_path, bodies):
    cfg = LLMConfig(mode="auto", cache_dir=tmp_path / "cache", trace_path=tmp_path / "trace.jsonl")
    fake = FakeClient(bodies)
    return LLMClient(cfg, client=fake), fake


def test_pipeline_produces_a_verified_reply_and_full_accounting(tmp_path, by_id, kb):
    llm, fake = make_llm(tmp_path, [body(classification_json()), body(draft_json())])
    rec = pipeline.run([by_id["MSG-003"]], llm, kb, max_workers=1)[0]
    assert rec.decision.action == "auto_reply_and_route" and rec.decision.queue == "pagos_conciliacion" and rec.decision.priority == "P2"
    assert rec.draft_reply.text == GOOD and rec.draft_reply.source == "llm" and rec.draft_reply.verifier.passed
    assert rec.draft_reply.kb_citations == ["pagos_y_cuotas.pagos_no_aplicados"]
    assert "DRAFT_VERIFIED" in rec.processing.rules_applied and rec.processing.llm_calls == 2
    assert rec.processing.input_tokens == 200 and rec.processing.cache_read_tokens == 4000 and rec.processing.cost_usd > 0
    assert rec.classification.entities.credit_number == "4471"          # rule extraction merged in
    assert len(fake.calls) == 2 and fake.calls[1]["system"][0]["text"].startswith("# Lumo reply drafter")
    assert rec.model_dump(mode="json")["classification"]["primary_reason"] == "pago_no_aplicado"


def test_pipeline_rejects_a_draft_that_fails_the_verifier(tmp_path, by_id, kb):
    bad = GOOD + " Te devolvemos el dinero en 3 días."
    llm, _ = make_llm(tmp_path, [body(classification_json()), body(draft_json(text=bad))])
    rec = pipeline.run([by_id["MSG-003"]], llm, kb, max_workers=1)[0]
    assert rec.decision.action == "route_to_human" and rec.decision.queue == "pagos_conciliacion"
    assert rec.draft_reply.text is None and rec.draft_reply.rejected_text == bad and not rec.draft_reply.verifier.passed
    assert {"VERIFIER_NUMBERS", "VERIFIER_FORBIDDEN_PHRASES"} <= set(rec.processing.rules_applied)


def test_pipeline_records_policy_gaps_from_the_draft(tmp_path, by_id, kb):
    otp_reply = ("¡Hola! Gracias por escribirnos. Si el código no te llega, verifica que el celular registrado sea el "
                 "correcto, espera 1 minuto y vuelve a intentar. El cambio de contraseña no lo podemos gestionar por "
                 "este canal; un asesor de soporte técnico te contactará. Quedamos atentos.")
    llm, _ = make_llm(tmp_path, [body(classification_json(primary_reason="cuenta_y_app")),
                                 body(draft_json(text=otp_reply, citations=("cuenta_app_seguridad.acceso_otp",),
                                                 uncovered=("El cambio de contraseña no está en la política.",)))])
    rec = pipeline.run([by_id["MSG-004"]], llm, kb, max_workers=1)[0]
    assert rec.decision.action == "auto_reply_and_route" and rec.decision.queue == "soporte_tecnico"
    assert rec.decision.policy_gap.startswith("El cambio de contraseña") and "GAP_ROUTED" in rec.processing.rules_applied
    llm2, _ = make_llm(tmp_path / "b", [body(classification_json(primary_reason="cuenta_y_app")), body(draft_json(can_answer=False, uncovered=("No hay flujo de contraseña.",)))])
    rec2 = pipeline.run([by_id["MSG-004"]], llm2, kb, max_workers=1)[0]
    assert rec2.decision.action == "route_to_human" and rec2.draft_reply.text is None and "DRAFT_NOT_ANSWERABLE" in rec2.processing.rules_applied


def test_pipeline_opens_a_case_for_a_known_policy_gap(tmp_path, by_id, kb):
    """MSG-166: password question answered with the OTP flow; the known gap still opens a support case."""
    otp_reply = ("¡Hola! El ingreso a la app es con tu documento y un código de verificación (OTP) que llega por SMS al "
                 "celular registrado. Verifica que ese número sea el correcto, espera 1 minuto y vuelve a intentar. Quedamos atentos.")
    llm, _ = make_llm(tmp_path, [body(classification_json(primary_reason="cuenta_y_app")),
                                 body(draft_json(text=otp_reply, citations=("cuenta_app_seguridad.acceso_otp",)))])
    rec = pipeline.run([by_id["MSG-166"]], llm, kb, max_workers=1)[0]
    assert rec.decision.action == "auto_reply_and_route" and rec.decision.queue == "soporte_tecnico"
    assert "password flow" in rec.decision.policy_gap and {"KNOWN_GAP", "GAP_ROUTED"} <= set(rec.processing.rules_applied)
    assert rec.draft_reply.text == otp_reply                                   # the covered part is still answered


def test_pipeline_handles_rules_templates_and_failures_without_the_model(tmp_path, by_id, kb):
    llm, fake = make_llm(tmp_path, [body(classification_json(primary_reason="consulta_saldo_cuotas", flags=Flags(fraud_or_security=True)))])
    recs = pipeline.run([by_id["MSG-192"], by_id["MSG-119"], by_id["MSG-016"]], llm, kb, max_workers=2)
    by = {r.id: r for r in recs}
    assert by["MSG-192"].draft_reply.source == "template" and by["MSG-192"].draft_reply.text.startswith("¡Hola!") and by["MSG-192"].processing.llm_calls == 0
    assert by["MSG-119"].decision.action == "close_no_reply" and by["MSG-119"].draft_reply.text is None
    fraud = by["MSG-016"]
    assert fraud.decision.priority == "P0" and fraud.decision.queue == "fraude" and fraud.draft_reply.source == "template"
    assert fraud.draft_reply.kb_citations == ["cuenta_app_seguridad.fraude_seguridad"] and fraud.draft_reply.verifier.passed
    assert len(fake.calls) == 1                                          # only MSG-016 needed the model, and no draft call


def test_pipeline_offline_miss_yields_a_routed_record(tmp_path, by_id, kb):
    cfg = LLMConfig(mode="offline", cache_dir=tmp_path / "cache", trace_path=None)
    rec = pipeline.run([by_id["MSG-003"]], LLMClient(cfg), kb, max_workers=1)[0]
    assert rec.classification is None and rec.decision.action == "route_to_human" and rec.decision.queue == "cx_general"
    assert "LLM_UNAVAILABLE" in rec.processing.rules_applied and "OfflineCacheMiss" in rec.processing.llm_error
