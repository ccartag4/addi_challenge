"""
Batch summary: what a CX lead needs to know about the whole batch, computed from the per-message
records and never from the model: volumes, what is auto-answerable, workload per queue and
priority, knowledge-base gaps in the customer's own terms, verifier rejections, duplicates,
low-confidence cases, model usage and cost. Written as JSON (machines) and Markdown (people).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

from .routing import PRIORITIES, ROUTING
from .schema import TAXONOMY, BatchSummary, TriageRecord

THRESHOLD = float(ROUTING["confidence_threshold"])
AUTO = ("auto_reply", "auto_reply_and_route")
CASE = ("auto_reply_and_route", "route_to_human")
REASON_NAMES = {r["id"]: r["name_es"] for r in TAXONOMY["reasons"]}


def _reason_of(r: TriageRecord) -> str:
    return r.classification.primary_reason.value if r.classification else "unclassified"


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f} %" if d else "-"


def build_summary(records: list[TriageRecord], *, pipeline_version: str, model: Optional[str],
                  live_calls: int, replays: int, spent_usd: Optional[float]) -> BatchSummary:
    n = len(records)
    by_channel = Counter(r.channel for r in records)
    by_reason = Counter(_reason_of(r) for r in records)
    by_priority = Counter(r.decision.priority for r in records)
    by_action = Counter(r.decision.action for r in records)
    by_queue = Counter(r.decision.queue for r in records if r.decision.action in CASE and r.decision.queue != "none")

    replies_ready = sum(1 for r in records if r.draft_reply.text)
    auto = sum(1 for r in records if r.decision.action in AUTO and r.draft_reply.text)
    drafts_ok = sum(1 for r in records if r.draft_reply.source == "llm" and r.draft_reply.text)
    drafts_failed = sum(1 for r in records if r.draft_reply.rejected_text)
    cases = sum(1 for r in records if r.decision.action in CASE)

    gaps: Counter = Counter()
    details: dict[str, list[str]] = defaultdict(list)
    for r in records:
        gap = r.decision.policy_gap
        if not gap:
            continue
        reason = _reason_of(r)
        if r.decision.policy_coverage == "none":
            gaps[f"{reason}: no policy"] += 1
            if gap not in details[reason]:
                details[reason].append(gap)
        else:
            gaps[f"{reason}: partially covered"] += 1
            details[reason].append(f"{r.id}: {gap}")

    flags: Counter = Counter()
    for r in records:
        if r.classification:
            for f in r.classification.flags.active():
                flags[f] += 1

    exact = sum(1 for r in records if r.dedup.duplicate_of)
    groups = Counter(r.dedup.near_duplicate_group for r in records if r.dedup.near_duplicate_group is not None)
    low_conf = sum(1 for r in records if r.classification and "LLM_CLASSIFIED" in r.processing.rules_applied
                   and r.classification.confidence < THRESHOLD)
    unclassified = sum(1 for r in records if r.classification is None)
    tokens = {
        "input": sum(r.processing.input_tokens for r in records),
        "cache_read": sum(r.processing.cache_read_tokens for r in records),
        "cache_write": sum(r.processing.cache_write_tokens for r in records),
        "output": sum(r.processing.output_tokens for r in records),
    }
    cost = round(sum(r.processing.cost_usd for r in records), 4)

    notable = _notable(records, n, auto, cases, drafts_failed, details, flags, exact, groups, low_conf, unclassified, by_reason)

    return BatchSummary(
        generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        pipeline_version=pipeline_version, model=model, messages=n,
        by_channel=dict(by_channel.most_common()), by_primary_reason=dict(by_reason.most_common()),
        by_priority={p: by_priority.get(p, 0) for p in PRIORITIES}, by_action=dict(by_action.most_common()),
        by_queue=dict(by_queue.most_common()),
        auto_answerable_share=round(auto / n, 4) if n else 0.0, replies_ready=replies_ready, cases_opened=cases,
        drafts_generated=drafts_ok, drafts_failed_verifier=drafts_failed,
        policy_gaps=dict(gaps.most_common()), policy_gap_details=dict(details),
        flags=dict(flags.most_common()),
        duplicates={"exact_duplicates_reused": exact, "near_duplicate_messages": sum(groups.values()),
                    "near_duplicate_groups": len(groups), "largest_near_duplicate_group": max(groups.values()) if groups else 0},
        low_confidence=low_conf, unclassified=unclassified,
        llm_calls=live_calls, response_cache_hits=replays, tokens=tokens, cost_usd=cost,
        spent_this_run_usd=None if spent_usd is None else round(spent_usd, 4), notable=notable,
    )


def _notable(records, n, auto, cases, drafts_failed, details, flags, exact, groups, low_conf, unclassified, by_reason) -> list[str]:
    out: list[str] = []
    out.append(f"{auto} of {n} messages ({_pct(auto, n)}) leave with a reply ready to send; {cases} ({_pct(cases, n)}) open a case for a person.")
    fraud = by_reason.get("fraude_seguridad", 0)
    if fraud:
        out.append(f"{fraud} security or fraud cases ({_pct(fraud, n)}) go to the fraud queue at P0 with the fixed safety acknowledgement.")
    if flags.get("requests_human"):
        out.append(f"{flags['requests_human']} customers explicitly asked for a person; {by_reason.get('hablar_con_humano', 0)} of them asked nothing else.")
    if flags.get("vulnerable_customer"):
        out.append(f"{flags['vulnerable_customer']} messages mention job loss, illness or a similar hardship and were raised to P1.")
    partial = {reason: [d for d in items if ": " in d] for reason, items in details.items()}
    partial = {k: v for k, v in partial.items() if v}
    if partial:
        top = sorted(partial.items(), key=lambda kv: -len(kv[1]))[:3]
        out.append("Knowledge-base gaps found while drafting: " + "; ".join(f"{REASON_NAMES.get(k, k)} ({len(v)})" for k, v in top)
                   + ". The customers' own requests are listed under policy gaps.")
    no_policy = sum(1 for r in records if r.decision.policy_gap and r.decision.policy_coverage == "none")
    if no_policy:
        out.append(f"{no_policy} messages fall on reasons the knowledge base does not cover at all (fees and rates, hours, application status, habeas data); they always reach a person.")
    if drafts_failed:
        checks = Counter()
        for r in records:
            if r.draft_reply.rejected_text and r.draft_reply.verifier:
                for c in r.draft_reply.verifier.checks:
                    if "FAIL" in c:
                        checks[c.split(":", 1)[0]] += 1
        out.append(f"{drafts_failed} model drafts were rejected by the verifier and routed to a person: " + ", ".join(f"{k} ({v})" for k, v in checks.most_common()) + ".")
    band = sum(1 for r in records if r.classification and "LLM_CLASSIFIED" in r.processing.rules_applied and THRESHOLD <= r.classification.confidence < 0.70)
    if low_conf or band:
        out.append(f"{low_conf} classifications fell below the {THRESHOLD:.2f} confidence threshold; {band} more sit between {THRESHOLD:.2f} and 0.69 and are worth a spot check.")
    if exact or groups:
        out.append(f"{exact} exact duplicates reused the original's result; {sum(groups.values())} messages sit in {len(groups)} near-duplicate groups (largest {max(groups.values()) if groups else 0}): repeated contacts or templated complaints.")
    days = Counter(r.received_at_utc[:10] for r in records)
    if days:
        day, k = days.most_common(1)[0]
        out.append(f"Busiest day: {day} with {k} messages ({_pct(k, n)}).")
    negative = sum(1 for r in records if r.classification and r.classification.sentiment == "negative")
    out.append(f"{negative} messages ({_pct(negative, n)}) carry negative sentiment.")
    if unclassified:
        out.append(f"{unclassified} messages could not be classified by the model and were routed to a person.")
    return out


def render_markdown(s: BatchSummary, records: list[TriageRecord]) -> str:
    n = s.messages
    L: list[str] = []
    add = L.append
    add("# Batch summary — Lumo contact triage")
    add("")
    add(f"Generated {s.generated_at_utc} by pipeline `{s.pipeline_version}`, model `{s.model}`. Computed from "
        f"`triage_results.jsonl` ({n} messages); nothing in this file was written by the model.")
    add("")
    add("## Headline")
    add("")
    add("| | |")
    add("|---|---:|")
    add(f"| Messages | {n} |")
    add(f"| Reply ready to send (auto-answerable) | {s.replies_ready} ({_pct(s.replies_ready, n)}) |")
    add(f"| of which model drafts that passed the verifier / fixed templates | {s.drafts_generated} / {s.replies_ready - s.drafts_generated} |")
    add(f"| Cases opened for a person | {s.cases_opened} ({_pct(s.cases_opened, n)}) |")
    add(f"| of which answered automatically and routed / needing a person's answer | {s.by_action.get('auto_reply_and_route', 0)} / {s.by_action.get('route_to_human', 0)} |")
    add(f"| Closed without reply (noise, closures) | {s.by_action.get('close_no_reply', 0)} |")
    add(f"| Model drafts rejected by the verifier | {s.drafts_failed_verifier} |")
    add(f"| Messages touching a knowledge-base gap | {sum(s.policy_gaps.values())} |")
    add(f"| Unclassified | {s.unclassified} |")
    add("")
    add("## What stands out")
    add("")
    for line in s.notable:
        add(f"- {line}")
    add("")
    add("## Volume by contact reason")
    add("")
    add("| Reason | n | share | reply ready | case opened | mean conf. |")
    add("|---|---:|---:|---:|---:|---:|")
    for reason, k in s.by_primary_reason.items():
        rs = [r for r in records if _reason_of(r) == reason]
        ready = sum(1 for r in rs if r.draft_reply.text)
        cases = sum(1 for r in rs if r.decision.action in CASE)
        confs = [r.classification.confidence for r in rs if r.classification]
        mean = f"{sum(confs) / len(confs):.2f}" if confs else "-"
        add(f"| `{reason}` — {REASON_NAMES.get(reason, '')} | {k} | {_pct(k, n)} | {ready} | {cases} | {mean} |")
    add("")
    add("## Actions, priorities and queues")
    add("")
    add("| Action | n |")
    add("|---|---:|")
    for a, k in s.by_action.items():
        add(f"| `{a}` | {k} |")
    add("")
    add("| Priority | SLA | n | of which cases for a person |")
    add("|---|---|---:|---:|")
    for p in PRIORITIES:
        sla = TAXONOMY["priorities"][p]["sla_hours"]
        cases = sum(1 for r in records if r.decision.priority == p and r.decision.action in CASE)
        add(f"| {p} ({TAXONOMY['priorities'][p]['label']}) | {f'{sla} h' if sla else '-'} | {s.by_priority.get(p, 0)} | {cases} |")
    add("")
    add("| Queue | cases | P0 | P1 | P2 | P3 |")
    add("|---|---:|---:|---:|---:|---:|")
    for q, k in s.by_queue.items():
        row = Counter(r.decision.priority for r in records if r.decision.queue == q and r.decision.action in CASE)
        add(f"| `{q}` | {k} | {row.get('P0', 0)} | {row.get('P1', 0)} | {row.get('P2', 0)} | {row.get('P3', 0)} |")
    add("")
    add("## Knowledge-base gaps (the signal the CX team asked for)")
    add("")
    add("| Gap | messages |")
    add("|---|---:|")
    for g, k in s.policy_gaps.items():
        add(f"| {g} | {k} |")
    add("")
    for reason, items in s.policy_gap_details.items():
        add(f"**{reason}** — {REASON_NAMES.get(reason, '')}")
        add("")
        for item in items:
            add(f"- {item}")
        add("")
    add("## Verifier rejections")
    add("")
    rejected = [r for r in records if r.draft_reply.rejected_text]
    if not rejected:
        add("None.")
    else:
        add("| id | reason | failed check | draft (kept for the agent, not sent) |")
        add("|---|---|---|---|")
        for r in rejected:
            fails = "; ".join(c for c in (r.draft_reply.verifier.checks if r.draft_reply.verifier else []) if "FAIL" in c)
            text = r.draft_reply.rejected_text.replace("|", "/").replace("\n", " ")
            add(f"| {r.id} | `{_reason_of(r)}` | {fails} | {text[:160]}{'…' if len(text) > 160 else ''} |")
    add("")
    add("## Flags")
    add("")
    add("| Flag | n |")
    add("|---|---:|")
    for f, k in s.flags.items():
        add(f"| `{f}` | {k} |")
    add("")
    add("## Duplicates and low confidence")
    add("")
    add(f"Exact duplicates reused: {s.duplicates['exact_duplicates_reused']}. Near-duplicate messages: "
        f"{s.duplicates['near_duplicate_messages']} in {s.duplicates['near_duplicate_groups']} groups "
        f"(largest {s.duplicates['largest_near_duplicate_group']}). Classifications below the routing threshold: {s.low_confidence}.")
    add("")
    low = sorted((r for r in records if r.classification and "LLM_CLASSIFIED" in r.processing.rules_applied and r.classification.confidence < 0.70),
                 key=lambda r: r.classification.confidence)
    if low:
        add("| id | conf. | reason | summary |")
        add("|---|---:|---|---|")
        for r in low:
            add(f"| {r.id} | {r.classification.confidence:.2f} | `{_reason_of(r)}` | {r.classification.summary.replace('|', '/')} |")
        add("")
    add("## Channels")
    add("")
    add(", ".join(f"{c}: {k}" for c, k in s.by_channel.items()) + ".")
    add("")
    add("## Model usage and cost")
    add("")
    add("| | |")
    add("|---|---:|")
    add(f"| Live model calls in this run | {s.llm_calls} |")
    add(f"| Responses replayed from cache in this run | {s.response_cache_hits} |")
    add(f"| Prompt tokens: uncached / cache read / cache write | {s.tokens['input']:,} / {s.tokens['cache_read']:,} / {s.tokens['cache_write']:,} |")
    add(f"| Output tokens (JSON plus thinking) | {s.tokens['output']:,} |")
    add(f"| Cost of the calls behind this output | USD {s.cost_usd:.2f} (≈ USD {s.cost_usd / n:.4f} per message) |" if n else "| Cost | - |")
    spent = "n/a (regenerated from file)" if s.spent_this_run_usd is None else f"USD {s.spent_this_run_usd:.2f}"
    add(f"| Spent by this run | {spent} |")
    add("")
    add("Reproduce: `./run.ps1` or `./run.sh` from `deliverables/` (offline from the committed cache without a key; live with `ANTHROPIC_API_KEY`).")
    return "\n".join(L) + "\n"
