"""
Evaluation harness: metric functions (oracle and null checks), gold-set loading, fixture file.
No API key needed.
"""
from __future__ import annotations

import pytest

from lumo_triage import eval as ev
from lumo_triage.schema import REASON_IDS


def test_reason_metrics_oracle_and_null():
    gold = ["pago_no_aplicado", "fecha_de_pago", "ruido", "pago_no_aplicado"]
    oracle = ev.reason_metrics([(g, g, []) for g in gold])
    assert oracle["exact_rate"] == 1.0 and oracle["lenient_rate"] == 1.0 and oracle["macro_f1"] == 1.0 and oracle["confusion"] == []
    null = ev.reason_metrics([(g, "pago_no_aplicado", []) for g in gold])            # constant prediction = majority class
    assert null["exact"] == 2 and null["exact_rate"] == 0.5 and null["macro_f1"] < 0.5
    assert null["per_class"]["fecha_de_pago"]["recall"] == 0.0 and null["per_class"]["pago_no_aplicado"]["precision"] == 0.5
    lenient = ev.reason_metrics([("cancelacion", "privacidad_habeas_data", ["privacidad_habeas_data"])])
    assert lenient["exact"] == 0 and lenient["lenient"] == 1


def test_priority_metrics_distance_and_direction():
    m = ev.priority_metrics([("P2", "P2"), ("P3", "P1"), ("P1", "P2"), ("P4", "P4")])
    assert m["exact"] == 2 and m["within_one"] == 3 and m["mean_abs_distance"] == pytest.approx(0.75)
    assert m["more_urgent_than_gold"] == 1 and m["less_urgent_than_gold"] == 1


def test_action_metrics_flag_the_unsafe_direction():
    m = ev.action_metrics([("route_to_human", "auto_reply"), ("auto_reply", "route_to_human"), ("auto_reply", "auto_reply_and_route"), ("close_no_reply", "close_no_reply")])
    assert m["exact"] == 1 and m["unsafe"] == 1 and m["conservative"] == 1 and m["auto_vs_auto_and_route"] == 1


def test_gold_set_loads_and_uses_only_known_labels():
    if not ev.GOLD_CSV.exists():
        pytest.skip("gold set not generated")
    gold = ev.load_gold()
    assert len(gold) == 90 and len({g.id for g in gold}) == 90
    assert all(g.reason in REASON_IDS and g.priority in {"P0", "P1", "P2", "P3", "P4"} for g in gold)
    # properties of the selection, not of the labels: a human correction may move a message
    # between reasons, so only the breadth of the set is asserted here
    assert len({g.reason for g in gold}) >= 20 and sum(1 for g in gold if g.reason == "fraude_seguridad") >= 2
    assert all(g.reviewed for g in gold) or sum(1 for g in gold if g.reviewed) == 0   # either fully reviewed or untouched


def test_adversarial_fixtures_are_well_formed():
    fixtures = ev.load_fixtures()
    assert len(fixtures) >= 8 and len({f["id"] for f in fixtures}) == len(fixtures)
    known = {"flag", "reason", "action", "priority", "queue", "no_reply", "reply_source", "language", "reply_language_es",
             "reply_must_not_contain", "document_number_none", "masked_kept", "llm_calls", "verifier_passed_if_reply"}
    for f in fixtures:
        assert set(f["expect"]) <= known, f["id"]
    msgs = ev.fixture_messages(fixtures)
    assert all(m.received_at_utc.endswith("Z") for m in msgs)
