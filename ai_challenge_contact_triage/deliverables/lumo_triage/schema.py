"""
Output contract of the triage component.

Two layers of models:
  * `Classification` — what the LLM returns (structured output). Only *what the message is*:
    reasons, confidence, flags, entities, sentiment, summary. No decisions.
  * `TriageRecord`   — the full per-message record written to the output file: classification
    plus the deterministic decision (priority, action, queue), the draft reply with its
    verification, and processing metadata.

The reason ids are loaded from policy/taxonomy.yaml so the prompt, the schema and the routing
policy cannot drift apart (tests/test_policy_consistency.py enforces it).
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

POLICY_DIR = Path(__file__).resolve().parent / "policy"


def _load_taxonomy() -> dict:
    with open(POLICY_DIR / "taxonomy.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


TAXONOMY = _load_taxonomy()
REASON_IDS: tuple[str, ...] = tuple(r["id"] for r in TAXONOMY["reasons"])
FLAG_IDS: tuple[str, ...] = tuple(TAXONOMY["flags"].keys())

Reason = Enum("Reason", {rid: rid for rid in REASON_IDS}, type=str)  # type: ignore[misc]

Priority = Literal["P0", "P1", "P2", "P3", "P4"]
Action = Literal["auto_reply", "auto_reply_and_route", "route_to_human", "close_no_reply"]
Sentiment = Literal["negative", "neutral", "positive"]
OutOfScopeKind = Literal["unrelated", "other_business_inquiry"]
PolicyCoverage = Literal["full", "partial", "none"]
ReplySource = Literal["llm", "template", "none"]


class Flags(BaseModel):
    """Cross-cutting signals; each one is a boolean so the routing policy can test it directly."""
    model_config = ConfigDict(extra="forbid")

    requests_human: bool = False
    fraud_or_security: bool = False
    legal_threat: bool = False
    collections_harassment: bool = False
    vulnerable_customer: bool = False
    imminent_deadline: bool = False
    repeat_contact: bool = False
    prompt_injection_suspected: bool = False
    pii_present: bool = False

    def active(self) -> list[str]:
        return [name for name, value in self.model_dump().items() if value]


class Entities(BaseModel):
    """Details present in the text. Every value must appear verbatim in the message (the
    pipeline verifies it and drops anything that does not); masked values are kept as written."""
    model_config = ConfigDict(extra="forbid")

    credit_number: Optional[str] = Field(None, description="Número de crédito u obligación, tal como aparece en el texto.")
    document_number: Optional[str] = Field(None, description="Documento de identidad, tal como aparece; si viene enmascarado, exactamente así.")
    amount: Optional[str] = Field(None, description="Monto mencionado, tal como aparece (por ejemplo '$185.000').")
    payment_date: Optional[str] = Field(None, description="Fecha o referencia temporal de un pago, tal como aparece ('04 de mayo', 'ayer').")
    transaction_reference: Optional[str] = Field(None, description="Referencia o número de transacción, tal como aparece.")
    payment_method_or_bank: Optional[str] = Field(None, description="Banco, billetera o medio de pago mencionado (PSE, Nequi, Efecty, Bancolombia...).")
    named_agent: Optional[str] = Field(None, description="Nombre de un asesor mencionado por el cliente.")
    masked_values: list[str] = Field(default_factory=list, description="Valores deliberadamente enmascarados por el cliente, sin completar.")


class Classification(BaseModel):
    """Structured output requested from the model."""
    model_config = ConfigDict(extra="forbid")

    primary_reason: Reason
    secondary_reasons: list[Reason] = Field(default_factory=list, max_length=3)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confianza en el motivo principal.")
    out_of_scope_kind: Optional[OutOfScopeKind] = None
    flags: Flags = Field(default_factory=Flags)
    entities: Entities = Field(default_factory=Entities)
    sentiment: Sentiment = "neutral"
    language: str = Field("es", description="Código ISO 639-1 del idioma del mensaje.")
    summary: str = Field(..., max_length=240, description="Una frase en español que resume la solicitud.")
    reasoning_brief: str = Field(..., max_length=300, description="Por qué ese motivo y esas banderas, en una o dos frases.")

    # The API enforces types and enums; the length and range constraints below are checked
    # client-side. They are repaired rather than rejected: a verbose model (Haiku 4.5 wrote a
    # 300+ character reasoning_brief for one message on every attempt) must not turn a correct
    # classification into "unclassified". Validators do not change the JSON schema, so the
    # committed response cache stays valid.
    @field_validator("summary", mode="before")
    @classmethod
    def _cap_summary(cls, v):
        return v[:240].rstrip() if isinstance(v, str) and len(v) > 240 else v

    @field_validator("reasoning_brief", mode="before")
    @classmethod
    def _cap_reasoning(cls, v):
        return v[:300].rstrip() if isinstance(v, str) and len(v) > 300 else v

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, v):
        return min(1.0, max(0.0, v)) if isinstance(v, (int, float)) else v

    @field_validator("secondary_reasons", mode="before")
    @classmethod
    def _cap_secondary(cls, v):
        return v[:3] if isinstance(v, list) and len(v) > 3 else v

    @field_validator("secondary_reasons")
    @classmethod
    def _no_duplicates(cls, v: list[Reason]) -> list[Reason]:
        seen: list[Reason] = []
        for r in v:
            if r not in seen:
                seen.append(r)
        return seen


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Priority
    sla_hours: Optional[int]
    action: Action
    queue: str
    policy_coverage: PolicyCoverage
    policy_gap: Optional[str] = Field(None, description="What the KB does not cover, when that shaped the decision.")
    reason_codes: list[str] = Field(default_factory=list, description="Override / bump / verifier codes that fired, in order.")


class VerifierResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    checks: list[str] = Field(default_factory=list, description="Each check as 'name: ok' or 'name: FAIL <detail>'.")


class DraftReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Optional[str] = Field(None, description="The reply to send; None when nothing may be sent automatically.")
    source: ReplySource = "none"
    kb_citations: list[str] = Field(default_factory=list, description="Section ids from taxonomy.yaml kb_sections.")
    verifier: Optional[VerifierResult] = None
    rejected_text: Optional[str] = Field(None, description="A model draft that failed the verifier or could not be sent; kept for audit, never sent.")


class Processing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_version: str
    rules_applied: list[str] = Field(default_factory=list)
    model: Optional[str] = Field(None, description="Model requested for this message, if any.")
    served_by: Optional[str] = Field(None, description="Model that actually answered (differs after a server-side refusal fallback).")
    effort: Optional[str] = None
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    response_cache_hits: int = Field(0, description="Responses replayed from the on-disk cache instead of a live call.")
    latency_ms: int = 0
    cost_usd: float = Field(0.0, description="What the LLM calls for this message cost when they were made (0 for rule-only messages).")
    llm_error: Optional[str] = Field(None, description="Set when the model could not classify the message (refusal, invalid output, API unavailable).")


class Dedup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_hash: str
    duplicate_of: Optional[str] = Field(None, description="id of an earlier message with identical normalised text.")
    near_duplicate_group: Optional[int] = None


class TriageRecord(BaseModel):
    """One JSON line per message in output/triage_results.jsonl."""
    model_config = ConfigDict(extra="forbid")

    id: str
    channel: Literal["chat", "email", "whatsapp"]
    received_at_utc: str
    sender: str
    dedup: Dedup
    classification: Optional[Classification] = Field(None, description="None only when the model failed; the decision then routes to a person.")
    decision: Decision
    draft_reply: DraftReply
    processing: Processing


class BatchSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at_utc: str
    pipeline_version: str
    model: Optional[str]
    messages: int
    by_channel: dict[str, int]
    by_primary_reason: dict[str, int]
    by_priority: dict[str, int]
    by_action: dict[str, int]
    by_queue: dict[str, int] = Field(description="Cases per queue (messages with a person involved).")
    auto_answerable_share: float = Field(description="Share of messages that leave with a reply ready to send.")
    replies_ready: int = Field(description="Messages with a sendable reply (model draft that passed the verifier, or a fixed template).")
    cases_opened: int = Field(description="Messages that need a person (auto_reply_and_route + route_to_human).")
    drafts_generated: int = Field(description="Model drafts that passed the verifier.")
    drafts_failed_verifier: int
    policy_gaps: dict[str, int] = Field(description="'<reason>: no policy' or '<reason>: partially covered' -> count")
    policy_gap_details: dict[str, list[str]] = Field(default_factory=dict, description="reason -> what the knowledge base did not cover, in the customer's terms")
    flags: dict[str, int]
    duplicates: dict[str, int] = Field(description="exact and near-duplicate counts")
    low_confidence: int = Field(description="Model classifications below the routing threshold (sent to a person).")
    unclassified: int = Field(0, description="Messages the model could not classify; routed to a person.")
    llm_calls: int = Field(description="Live model calls made by this run.")
    response_cache_hits: int = Field(description="Model responses replayed from the on-disk cache by this run.")
    tokens: dict[str, int]
    cost_usd: float = Field(description="Cost of the LLM calls behind this output when they were made.")
    spent_this_run_usd: Optional[float] = Field(0.0, description="Cost actually incurred by this run (0 when fully replayed; null when the summary was regenerated from the file).")
    notable: list[str] = Field(default_factory=list, description="Anything a CX lead should look at.")
