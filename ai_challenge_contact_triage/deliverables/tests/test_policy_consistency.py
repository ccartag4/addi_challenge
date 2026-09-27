"""
The taxonomy, the routing policy, the knowledge base and the schema must agree with each other.
These tests run without any API key.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from lumo_triage import schema

DELIVERABLES = Path(__file__).resolve().parents[1]
KB_DIR = DELIVERABLES.parent / "knowledge_base"
DATA = DELIVERABLES.parent / "data" / "messages.jsonl"


def load(name: str) -> dict:
    with open(schema.POLICY_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


TAX = load("taxonomy.yaml")
ROUTING = load("routing.yaml")
ACTIONS = set(ROUTING["actions"])
QUEUES = set(ROUTING["queues"])
PRIORITIES = set(TAX["priorities"])


def test_reason_ids_are_unique_and_snake_case():
    ids = [r["id"] for r in TAX["reasons"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z_]+", i) for i in ids)


def test_schema_enum_matches_taxonomy():
    assert tuple(m.value for m in schema.Reason) == schema.REASON_IDS
    assert set(schema.Flags.model_fields) == set(TAX["flags"])


def test_every_reason_has_valid_defaults():
    for r in TAX["reasons"]:
        assert r["default_action"] in ACTIONS, r["id"]
        assert r["default_queue"] in QUEUES, r["id"]
        assert r["base_priority"] in PRIORITIES, r["id"]
        assert r["policy_coverage"] in {"full", "partial", "none"}, r["id"]
        assert r["reply_source"] in {"llm", "template", "none"}, r["id"]
        assert r["origin"] in {"original", "added"}, r["id"]
        assert r["examples"], f"{r['id']} needs example message ids"


def test_reasons_without_policy_never_draft_with_the_model():
    for r in TAX["reasons"]:
        if r["policy_coverage"] == "none":
            assert r["reply_source"] != "llm", f"{r['id']} has no policy but would draft with the model"
        if r["reply_source"] == "llm":
            assert r["kb_sections"], f"{r['id']} drafts with the model but cites no KB section"


def test_kb_section_ids_exist_in_the_knowledge_base_files():
    for sid, meta in TAX["kb_sections"].items():
        path = KB_DIR / meta["file"]
        assert path.exists(), f"{sid}: {meta['file']} missing"
        headings = re.findall(r"^##\s+(.+?)\s*$", path.read_text(encoding="utf-8"), re.M)
        assert meta["heading"] in headings, f"{sid}: heading {meta['heading']!r} not in {meta['file']} ({headings})"


def test_every_reason_cites_known_sections():
    known = set(TAX["kb_sections"])
    for r in TAX["reasons"]:
        for sid in r["kb_sections"]:
            assert sid in known, f"{r['id']} cites unknown section {sid}"


def test_overrides_reference_known_values():
    for o in ROUTING["overrides"]:
        assert o["action"] in ACTIONS, o["code"]
        assert o["queue"] in QUEUES or o["queue"] == "reason_default_or_cx_general", o["code"]
        assert o["min_priority"] in PRIORITIES, o["code"]
        cond = o["when"]
        for key in cond:
            assert key in {"flag", "any_flag", "confidence_below_threshold", "policy_coverage", "reason", "out_of_scope_kind"}, o["code"]
        if "flag" in cond:
            assert cond["flag"] in TAX["flags"], o["code"]
        if "any_flag" in cond:
            assert set(cond["any_flag"]) <= set(TAX["flags"]), o["code"]
        if "template" in o:
            assert o["template"] in ROUTING["templates"], o["code"]
        if "reason" in cond:
            assert cond["reason"] in schema.REASON_IDS, o["code"]


def test_example_message_ids_exist_and_are_not_reused_across_reasons():
    ids = {line.split('"id": "')[1].split('"')[0] for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()}
    seen: dict[str, str] = {}
    for r in TAX["reasons"]:
        for mid in r["examples"]:
            assert mid in ids, f"{r['id']}: {mid} not in messages.jsonl"
            assert mid not in seen, f"{mid} used as example for both {seen[mid]} and {r['id']}"
            seen[mid] = r["id"]


def test_templates_are_spanish_and_short():
    for name, text in ROUTING["templates"].items():
        assert len(text.split()) <= ROUTING["verifier"]["max_words"], name
        assert not re.search(r"\b(the|please|your)\b", text, re.I), f"{name} looks English"
