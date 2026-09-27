"""
End-to-end assembly of one `TriageRecord` per message:

    normalise -> rules -> classification -> routing -> (template | grounded draft -> verifier) -> record

Stage 1 (classification) and stage 2 (drafting) each run in a small thread pool through the
same cached, traced LLM client. Every adjustment made by code leaves a code in
`processing.rules_applied`, so a reviewer can reconstruct why a message ended where it did.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from .classify import PROMPT_VERSION, ClassifiedMessage, classify_messages
from .draft import DRAFT_PROMPT_VERSION, draft_reply
from .kb import KnowledgeBase, load_kb
from .llm import LLMClient, LLMResult
from .normalize import Message
from .routing import ROUTING, Plan, known_gaps, route
from .schema import Dedup, DraftReply, Processing, TriageRecord
from .verify import DraftCheckInput, failed_checks, verify

PIPELINE_VERSION = f"0.4.0 ({PROMPT_VERSION}, {DRAFT_PROMPT_VERSION})"


def _human_queue(plan: Plan) -> str:
    if plan.decision.queue != "none":
        return plan.decision.queue
    reason = plan.reason or {}
    return reason.get("default_queue") if reason.get("default_queue") not in (None, "none") else "cx_general"


def _accumulate(proc: Processing, result: Optional[LLMResult]) -> None:
    if result is None:
        return
    proc.llm_calls += 0 if result.from_cache else 1
    proc.response_cache_hits += 1 if result.from_cache else 0
    proc.input_tokens += result.input_tokens
    proc.output_tokens += result.output_tokens
    proc.cache_read_tokens += result.cache_read_tokens
    proc.cache_write_tokens += result.cache_write_tokens
    proc.latency_ms += result.latency_ms
    proc.cost_usd += result.cost_usd
    proc.served_by = result.served_by or proc.served_by


def triage_message(cm: ClassifiedMessage, llm: LLMClient, kb: KnowledgeBase) -> TriageRecord:
    m: Message = cm.message
    cls = cm.classification
    plan = route(cls)
    decision = plan.decision
    codes = list(cm.rules_applied) + list(decision.reason_codes)
    proc = Processing(pipeline_version=PIPELINE_VERSION, model=llm.cfg.model if (cm.llm or plan.draft_allowed) else None,
                      effort=llm.cfg.effort if (cm.llm or plan.draft_allowed) else None, llm_error=cm.error)
    _accumulate(proc, cm.llm)
    draft = DraftReply(source="none")

    if cls is not None and plan.template:
        text = ROUTING["templates"][plan.template].strip()
        citations = list(ROUTING.get("template_citations", {}).get(plan.template, []))
        result = verify(DraftCheckInput(text, citations, citations, kb, m.text, cls.entities, source="template", rules=ROUTING["verifier"]))
        draft = DraftReply(text=text if result.passed else None, source="template", kb_citations=citations,
                           verifier=result, rejected_text=None if result.passed else text)
        if not result.passed:
            decision.action = "route_to_human"
            codes += [f"VERIFIER_{c.upper()}" for c in failed_checks(result)]
        codes.append(f"TEMPLATE_{plan.template.upper()}")

    elif cls is not None and plan.draft_allowed:
        out, result, error = draft_reply(m, cls, plan, kb, llm)
        _accumulate(proc, result)
        if error is not None:
            decision.action = "route_to_human"
            proc.llm_error = error
            codes.append("DRAFT_FAILED")
        elif not out.can_answer or not out.reply_text:
            decision.action = "route_to_human"
            decision.policy_gap = "; ".join(out.uncovered_points) or "The allowed sections do not answer the request."
            codes.append("DRAFT_NOT_ANSWERABLE")
        else:
            check = verify(DraftCheckInput(out.reply_text, out.citations, plan.allowed_sections, kb, m.text,
                                           cls.entities, source="llm", rules=ROUTING["verifier"]))
            if check.passed:
                draft = DraftReply(text=out.reply_text.strip(), source="llm", kb_citations=out.citations, verifier=check)
                codes.append("DRAFT_VERIFIED")
                if out.uncovered_points:
                    decision.policy_gap = "; ".join(out.uncovered_points)
                    if decision.action == "auto_reply":
                        decision.action = "auto_reply_and_route"
                        decision.queue = _human_queue(plan)
                    codes.append("GAP_ROUTED")
            else:
                draft = DraftReply(text=None, source="none", kb_citations=out.citations, verifier=check, rejected_text=out.reply_text)
                decision.action = "route_to_human"
                codes += [f"VERIFIER_{c.upper()}" for c in failed_checks(check)]

    # known policy holes detected by pattern in the customer's text (taxonomy.yaml known_gaps)
    if cls is not None:
        for gap in known_gaps(cls.primary_reason.value, m.text):
            if gap not in (decision.policy_gap or ""):
                decision.policy_gap = f"{decision.policy_gap}; {gap}" if decision.policy_gap else gap
                codes.append("KNOWN_GAP")
            if decision.action == "auto_reply" and draft.text:
                decision.action = "auto_reply_and_route"
                decision.queue = _human_queue(plan)
                if "GAP_ROUTED" not in codes:
                    codes.append("GAP_ROUTED")

    # safety net: an auto action must carry a sendable reply
    if decision.action in ("auto_reply", "auto_reply_and_route") and not draft.text:
        decision.action = "route_to_human"
        codes.append("NO_REPLY_TEXT")
    if decision.action == "route_to_human" and decision.queue == "none":
        decision.queue = _human_queue(plan)
    decision.reason_codes = codes
    proc.rules_applied = codes

    return TriageRecord(
        id=m.id, channel=m.channel, received_at_utc=m.received_at_utc, sender=m.sender,
        dedup=Dedup(content_hash=m.content_hash, duplicate_of=m.duplicate_of, near_duplicate_group=m.near_duplicate_group),
        classification=cls, decision=decision, draft_reply=draft, processing=proc,
    )


def run(messages: list[Message], llm: LLMClient, kb: Optional[KnowledgeBase] = None, max_workers: int = 4,
        on_classified: Optional[Callable[[ClassifiedMessage], None]] = None,
        on_done: Optional[Callable[[TriageRecord], None]] = None) -> list[TriageRecord]:
    kb = kb or load_kb()
    classified = classify_messages(messages, llm, max_workers=max_workers, on_done=on_classified)

    def one(cm: ClassifiedMessage) -> TriageRecord:
        rec = triage_message(cm, llm, kb)
        if on_done:
            on_done(rec)
        return rec

    # drafting stage: the first model-bound draft alone (writes the prompt cache), the rest in a pool
    needs_model = [cm for cm in classified if cm.classification is not None and route(cm.classification).draft_allowed]
    results: dict[str, TriageRecord] = {}
    if needs_model:
        results[needs_model[0].message.id] = one(needs_model[0])
    rest = [cm for cm in classified if cm.message.id not in results]
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        for rec in pool.map(one, rest):
            results[rec.id] = rec
    return [results[m.id] for m in messages]
