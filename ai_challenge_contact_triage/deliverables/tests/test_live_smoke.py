"""
Live smoke test against the real API: three messages with unambiguous reasons. It costs a few
cents and needs a key, so it only runs with LUMO_LIVE_TESTS=1. It is the standing check the
caching guide asks for: the second and third calls must read the cached system prefix.

    $env:LUMO_LIVE_TESTS = "1"; python -m pytest tests/test_live_smoke.py -q -m live
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from lumo_triage import classify, normalize
from lumo_triage.llm import LLMClient, LLMConfig

DATA = Path(__file__).resolve().parents[1].parent / "data" / "messages.jsonl"

pytestmark = pytest.mark.live
live_enabled = os.environ.get("LUMO_LIVE_TESTS") == "1"


@pytest.mark.skipif(not live_enabled, reason="set LUMO_LIVE_TESTS=1 to spend a few cents on a live check")
def test_live_classification_and_prompt_cache(tmp_path):
    cfg = LLMConfig.from_env(mode="live")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("no ANTHROPIC_API_KEY")
    cfg = LLMConfig(model=cfg.model, effort=cfg.effort, mode="live", cache_dir=tmp_path / "cache", trace_path=tmp_path / "trace.jsonl")
    client = LLMClient(cfg)
    by_id = {m.id: m for m in normalize.prepare(DATA)}
    expected = {"MSG-003": "pago_no_aplicado", "MSG-016": "fraude_seguridad", "MSG-037": "fuera_de_alcance"}

    results = {}
    for mid in expected:                                   # sequential on purpose: the cache must be warm for call 2
        results[mid] = classify.classify_one(by_id[mid], client)

    for mid, reason in expected.items():
        r = results[mid]
        assert r.classification is not None, r.error
        assert r.classification.primary_reason.value == reason, (mid, r.classification.primary_reason, r.classification.reasoning_brief)
        assert r.llm.stop_reason == "end_turn" and r.llm.served_by
    assert results["MSG-016"].classification.flags.fraud_or_security
    assert results["MSG-037"].classification.out_of_scope_kind == "unrelated"
    assert results["MSG-003"].classification.entities.credit_number == "4471"

    reads = [results[m].llm.cache_read_tokens for m in expected]
    writes = [results[m].llm.cache_write_tokens for m in expected]
    assert writes[0] > 0 or reads[0] > 0, "first call should write (or read a still-warm) prefix"
    assert reads[1] > 0 and reads[2] > 0, f"prompt cache not read on later calls: reads={reads} writes={writes}"
