"""
Routing engine: (classification) -> (priority, action, queue) plus what the drafting stage may
do. Pure code over `policy/routing.yaml` and `policy/taxonomy.yaml`; no model involved, so the
CX team can change the policy without touching a prompt and every decision lists the codes
that produced it.

Evaluation order (routing.yaml): overrides first, first match wins; then the reason defaults;
then priority: the most urgent base priority among primary and secondary reasons, raised to
the override's minimum, then the flag bumps. A reply source is resolved last: an override
template, the reason's template, or a model draft when the reason has policy coverage; when an
auto-reply action ends up with no possible reply, it degrades to `route_to_human`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

from .schema import POLICY_DIR, TAXONOMY, Classification, Decision


def _load_routing() -> dict:
    with open(POLICY_DIR / "routing.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


ROUTING = _load_routing()
PRIORITIES: list[str] = list(TAXONOMY["priorities"].keys())          # P0 (most urgent) .. P4
REASONS: dict[str, dict] = {r["id"]: r for r in TAXONOMY["reasons"]}
AUTO_ACTIONS = ("auto_reply", "auto_reply_and_route")


def more_urgent(a: str, b: str) -> str:
    return a if PRIORITIES.index(a) <= PRIORITIES.index(b) else b


def bump(priority: str, levels: int) -> str:
    return PRIORITIES[max(0, PRIORITIES.index(priority) - levels)]


def sla_for(priority: str) -> Optional[int]:
    return TAXONOMY["priorities"][priority]["sla_hours"]


def section_ids_for(reasons: list[str], extra: Optional[list[str]] = None) -> list[str]:
    out: list[str] = []
    for reason in reasons:
        for sid in REASONS.get(reason, {}).get("kb_sections", []):
            if sid not in out:
                out.append(sid)
    for sid in extra or []:
        if sid not in out:
            out.append(sid)
    return out


@dataclass
class Plan:
    """The decision plus the drafting directives derived from it."""
    decision: Decision
    draft_allowed: bool = False                 # a grounded model draft may be attempted
    template: Optional[str] = None              # name of a fixed reply in routing.yaml
    reply_source: str = "none"                  # llm | template | none
    allowed_sections: list[str] = field(default_factory=list)
    reason: Optional[dict] = None


def _matches(when: dict[str, Any], cls: Classification, reason: dict, threshold: float) -> bool:
    """All keys of `when` must hold."""
    secondary = [r.value for r in cls.secondary_reasons]
    for key, value in when.items():
        if key == "flag" and not getattr(cls.flags, value):
            return False
        if key == "any_flag" and not any(getattr(cls.flags, f) for f in value):
            return False
        if key == "confidence_below_threshold" and (cls.confidence < threshold) != bool(value):
            return False
        if key == "policy_coverage" and reason["policy_coverage"] != value:
            return False
        if key == "reply_source" and reason["reply_source"] != value:
            return False
        if key == "reason" and cls.primary_reason.value != value:
            return False
        if key == "out_of_scope_kind" and cls.out_of_scope_kind != value:
            return False
        if key == "any_reason" and value != cls.primary_reason.value and value not in secondary:
            return False
    return True


def _queue(spec: str, reason: dict) -> str:
    if spec == "reason_default_or_cx_general":
        return reason["default_queue"] if reason["default_queue"] != "none" else "cx_general"
    return spec


def route(cls: Optional[Classification], policy: dict = ROUTING) -> Plan:
    if cls is None:
        decision = Decision(priority="P3", sla_hours=sla_for("P3"), action="route_to_human", queue="cx_general",
                            policy_coverage="none",
                            policy_gap="Classification unavailable: the model did not return a valid result.",
                            reason_codes=["LLM_UNAVAILABLE"])
        return Plan(decision=decision)

    primary = cls.primary_reason.value
    reason = REASONS[primary]
    secondary = [r.value for r in cls.secondary_reasons]
    codes: list[str] = []

    # 1. overrides, first match wins
    action, queue, reply_source = reason["default_action"], reason["default_queue"], reason["reply_source"]
    min_priority: Optional[str] = None
    no_draft = False
    template: Optional[str] = None
    extra_sections: list[str] = []
    threshold = float(policy["confidence_threshold"])
    for o in policy["overrides"]:
        if _matches(o["when"], cls, reason, threshold):
            codes.append(o["code"])
            action = o["action"]
            queue = _queue(o["queue"], reason)
            min_priority = o.get("min_priority")
            no_draft = bool(o.get("no_draft", False))
            template = o.get("template")
            extra_sections = list(o.get("extra_sections", []))
            break

    # 2. priority: base (primary or a more urgent secondary), override minimum, flag bumps
    priority = reason["base_priority"]
    for s in secondary:
        sp = REASONS[s]["base_priority"]
        if PRIORITIES.index(sp) < PRIORITIES.index(priority):
            priority = sp
            codes.append(f"PRIO_SECONDARY_{s.upper()}")
    if min_priority is not None:
        priority = more_urgent(priority, min_priority)
    for flag_name, spec in policy["priority_bumps"].items():
        if getattr(cls.flags, flag_name, False):
            before = priority
            priority = bump(priority, int(spec.get("levels", 0)))
            if spec.get("floor"):
                priority = more_urgent(priority, spec["floor"])
            if priority != before:
                codes.append(f"BUMP_{flag_name.upper()}")

    # 3. reply source
    if template is None and reply_source == "template" and action in AUTO_ACTIONS and not no_draft:
        template = policy.get("reason_templates", {}).get(primary)
    if template is not None:
        reply_source = "template"
    coverage = reason["policy_coverage"]
    allowed = section_ids_for([primary] + secondary, extra_sections)
    draft_allowed = (action in AUTO_ACTIONS and not no_draft and template is None
                     and reply_source == "llm" and coverage in ("full", "partial") and bool(allowed))
    if action in AUTO_ACTIONS and not draft_allowed and template is None:
        action = "route_to_human"
        codes.append("NO_REPLY_SOURCE")
    if action == "route_to_human" and queue == "none":
        queue = _queue("reason_default_or_cx_general", reason)
    if action in ("close_no_reply", "auto_reply"):
        queue = "none"                      # a reason's default_queue only applies when a person is involved
    if not (draft_allowed or template):
        reply_source = "none"

    decision = Decision(priority=priority, sla_hours=sla_for(priority), action=action, queue=queue,
                        policy_coverage=coverage,
                        policy_gap=reason.get("policy_gap") if coverage == "none" else None,
                        reason_codes=codes)
    return Plan(decision=decision, draft_allowed=draft_allowed, template=template,
                reply_source=reply_source, allowed_sections=allowed, reason=reason)
