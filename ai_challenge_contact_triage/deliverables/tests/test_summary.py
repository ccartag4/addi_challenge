"""
Batch summary and reproducibility. The summary is computed from records only; the determinism
test replays the committed cache offline and compares with the committed output.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumo_triage import normalize, pipeline
from lumo_triage.kb import load_kb
from lumo_triage.llm import DEFAULT_CACHE_DIR, LLMClient, LLMConfig
from lumo_triage.schema import TriageRecord
from lumo_triage.summary import build_summary, render_markdown

DELIVERABLES = Path(__file__).resolve().parents[1]
RESULTS = DELIVERABLES / "output" / "triage_results.jsonl"
DATA = DELIVERABLES.parent / "data" / "messages.jsonl"


@pytest.fixture(scope="module")
def records():
    if not RESULTS.exists():
        pytest.skip("output/triage_results.jsonl not generated yet")
    return [TriageRecord.model_validate_json(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_summary_counts_are_consistent_with_the_records(records):
    s = build_summary(records, pipeline_version="test", model="claude-opus-5", live_calls=0, replays=len(records), spent_usd=0.0)
    n = len(records)
    assert s.messages == n == sum(s.by_action.values()) == sum(s.by_primary_reason.values()) == sum(s.by_channel.values())
    assert sum(s.by_priority.values()) == n and set(s.by_priority) == {"P0", "P1", "P2", "P3", "P4"}
    assert s.replies_ready == sum(1 for r in records if r.draft_reply.text)
    assert s.replies_ready == s.drafts_generated + sum(1 for r in records if r.draft_reply.source == "template" and r.draft_reply.text)
    assert 0.0 <= s.auto_answerable_share <= 1.0 and abs(s.auto_answerable_share * n - s.replies_ready) < 1
    assert s.cases_opened == s.by_action.get("auto_reply_and_route", 0) + s.by_action.get("route_to_human", 0)
    assert s.cases_opened == sum(s.by_queue.values())                                     # every case has a queue
    assert sum(s.policy_gaps.values()) == sum(1 for r in records if r.decision.policy_gap)
    assert s.drafts_failed_verifier == sum(1 for r in records if r.draft_reply.rejected_text)
    assert s.cost_usd == pytest.approx(sum(r.processing.cost_usd for r in records), abs=1e-3)
    assert s.duplicates["exact_duplicates_reused"] == 2 and s.duplicates["near_duplicate_messages"] == 55
    assert s.notable and s.notable[0].startswith(f"{s.replies_ready} of {n} messages")


def test_markdown_report_has_every_section_and_no_model_text_leaks(records):
    s = build_summary(records, pipeline_version="test", model="claude-opus-5", live_calls=0, replays=0, spent_usd=None)
    md = render_markdown(s, records)
    for heading in ("## Headline", "## What stands out", "## Volume by contact reason", "## Actions, priorities and queues",
                    "## Knowledge-base gaps", "## Verifier rejections", "## Flags", "## Duplicates and low confidence", "## Model usage and cost"):
        assert heading in md, heading
    assert "n/a (regenerated from file)" in md
    top_reason = next(iter(s.by_primary_reason))
    assert f"`{top_reason}`" in md
    json.dumps(s.model_dump(mode="json"))                                                  # serialisable


def test_offline_replay_reproduces_the_committed_records(records):
    """The definition of done: a fresh offline run equals the committed output."""
    committed = {r.id: r.model_dump(mode="json") for r in records}
    messages = normalize.prepare(DATA)[:40]
    if not DEFAULT_CACHE_DIR.exists():
        pytest.skip("no committed cache")
    cfg = LLMConfig(mode="offline", cache_dir=DEFAULT_CACHE_DIR, trace_path=None)
    fresh = pipeline.run(messages, LLMClient(cfg), load_kb(), max_workers=4)
    for rec in fresh:
        assert rec.model_dump(mode="json") == committed[rec.id], rec.id
