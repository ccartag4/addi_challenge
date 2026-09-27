"""
Verifier for reply drafts: code, not prompt. Rules live in `policy/routing.yaml` (`verifier`).

A draft passes only if every check passes; any failure downgrades the action to
`route_to_human` with the code VERIFIER_<check>, and the text is kept as `rejected_text` for
audit. Checks:
  citations         at least one citation, all inside the sections allowed for the message
  numbers           every number in the reply (digits or number words) appears in a cited
                    section or in the customer's own message
  forbidden_phrases none of the forbidden promises or requests (accent-insensitive)
  no_document_echo  the customer's document number or any card number is not repeated
  length            between min_words and max_words
  language          Spanish (function words present, no English markers)
  no_placeholders   no [brackets], {braces}, XXX or similar left in the text
  contact_details   e-mails and URLs only if they appear in a cited section
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .kb import KnowledgeBase, digits_in
from .normalize import canonical_tokens
from .schema import Entities, VerifierResult

NUMBER_WORDS = {"dos": "2", "tres": "3", "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7", "ocho": "8",
                "nueve": "9", "diez": "10", "quince": "15", "veinte": "20", "treinta": "30", "sesenta": "60"}
# "primer/primera" is left out on purpose: "desde el primer día" is idiom, not a policy figure
ORDINALS = {"segunda": "2", "segundo": "2", "tercera": "3", "tercer": "3",
            "cuarta": "4", "cuarto": "4", "quinta": "5", "quinto": "5"}
UNIT = r"(?:d[ií]as?|horas?|minutos?|semanas?|mes(?:es)?|veces|vez|intentos?|a[nñ]os?|cuotas?|pagos?)"
WORD_NUMBER = re.compile(rf"\b({'|'.join(NUMBER_WORDS)})\s+{UNIT}\b", re.I)
ORDINAL = re.compile(rf"\b({'|'.join(ORDINALS)})\s+{UNIT}\b", re.I)
SPANISH_STOPWORDS = {"de", "la", "el", "que", "en", "tu", "te", "para", "por", "con", "los", "las", "un", "una",
                     "puedes", "nos", "si", "del", "al", "es", "se", "no", "lo", "tus", "más", "mas", "desde", "hasta"}
ENGLISH_MARKERS = re.compile(r"\b(the|please|your|you|we|thanks|hello|and|with)\b", re.I)
# brackets in any case; word placeholders only in upper case ("todo actualizado" is Spanish, "TODO" is a leftover)
PLACEHOLDER_ANY = re.compile(r"[\[\]{}<>]")
PLACEHOLDER_UPPER = re.compile(r"\bX{3,}\b|\bNOMBRE\b|\bTODO\b|\bFIXME\b|\bTBD\b")


def numbers_in(text: str) -> set[str]:
    """Digit strings for numerals, number words with a unit ('dos veces') and ordinals
    ('tercera vez') in a text. Used on the reply and, for the allowed side, on the message."""
    found = digits_in(text)
    found |= {NUMBER_WORDS[m.group(1).lower()] for m in WORD_NUMBER.finditer(text)}
    found |= {ORDINALS[m.group(1).lower()] for m in ORDINAL.finditer(text)}
    return found
EMAIL_OR_URL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|https?://\S+|www\.\S+", re.I)
CARD = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b")


def _norm(text: str) -> str:
    return " ".join(canonical_tokens(text))


@dataclass
class DraftCheckInput:
    reply_text: str
    citations: list[str]
    allowed_sections: list[str]
    kb: KnowledgeBase
    message_text: str
    entities: Entities
    source: str = "llm"                          # llm | template
    rules: dict = field(default_factory=dict)


def verify(inp: DraftCheckInput) -> VerifierResult:
    rules = inp.rules
    checks: list[str] = []
    failed = False

    def record(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failed
        checks.append(f"{name}: ok" if ok else f"{name}: FAIL {detail}".rstrip())
        failed = failed or not ok

    reply = inp.reply_text or ""
    cited = inp.kb.get(inp.citations)
    cited_text = "\n".join(s.text for s in cited)

    # citations
    if inp.source == "llm" and rules.get("require_citations", True):
        unknown = [c for c in inp.citations if c not in inp.kb.sections]
        outside = [c for c in inp.citations if c in inp.kb.sections and c not in inp.allowed_sections]
        if not inp.citations:
            record("citations", False, "no section cited")
        elif unknown or outside:
            record("citations", False, f"unknown={unknown} outside_allowed={outside}")
        else:
            record("citations", True)

    # numbers
    if rules.get("numbers_must_appear_in_cited_sections", True):
        allowed_digits = digits_in(cited_text) | numbers_in(inp.message_text)
        stray = sorted(d for d in numbers_in(reply) if d and d not in allowed_digits)
        record("numbers", not stray, f"not in cited sections or message: {stray}" if stray else "")

    # forbidden phrases
    norm_reply = _norm(reply)
    hits = [p for p in rules.get("forbidden_phrases", []) if _norm(p) and _norm(p) in norm_reply]
    record("forbidden_phrases", not hits, f"{hits}" if hits else "")

    # document echo
    echoed = []
    reply_digits = re.sub(r"\D", "", reply)
    for name in rules.get("never_echo_entities", ["document_number"]):
        value = getattr(inp.entities, name, None)
        if value:
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 5 and digits in reply_digits:
                echoed.append(name)
    if CARD.search(reply):
        echoed.append("card_number")
    record("no_document_echo", not echoed, f"{echoed}" if echoed else "")

    # length
    words = len(reply.split())
    max_words = int(rules.get("max_words", 160))
    min_words = int(rules.get("min_words", 8))
    record("length", min_words <= words <= max_words, f"{words} words (allowed {min_words}-{max_words})")

    # language
    tokens = canonical_tokens(reply)
    spanish = sum(1 for t in tokens if t in SPANISH_STOPWORDS)
    english = ENGLISH_MARKERS.findall(reply)
    record("language", spanish >= 3 and not english, f"spanish_function_words={spanish} english_markers={english}")

    # placeholders
    ph = PLACEHOLDER_ANY.search(reply) or PLACEHOLDER_UPPER.search(reply)
    record("no_placeholders", ph is None, f"found {ph.group(0)!r}" if ph else "")

    # contact details
    stray_contacts = [c for c in EMAIL_OR_URL.findall(reply) if c.rstrip(".,;") not in cited_text]
    record("contact_details", not stray_contacts, f"{stray_contacts}" if stray_contacts else "")

    return VerifierResult(passed=not failed, checks=checks)


def failed_checks(result: VerifierResult) -> list[str]:
    return [c.split(":", 1)[0] for c in result.checks if ": FAIL" in c]
