"""
Deterministic entity extraction, and the verifier that keeps any entity (ours or the model's)
honest: a value is kept only if it appears verbatim in the message text.

Design rules:
* Extract what is *present*; never normalise a value into something the customer did not write
  ('$185.000' stays '$185.000').
* A deliberately masked identifier ('1.0xx.xxx.xxx', '1.020.XXX.XXX') is reported under
  `masked_values` and never completed or treated as a document number.
* Colombian conventions: '.' is the thousands separator ('185.000'), amounts may carry '$',
  dates are written '04 de mayo' or as a weekday ('el lunes').
"""
from __future__ import annotations

import re
from typing import Optional

from .schema import Entities

MONTHS = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre"
WEEKDAYS = "lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo"

RE_MASKED = re.compile(r"\b\d[\d\.]*[xX]{2,}[\dxX\.]*\b")
RE_CREDIT = re.compile(
    r"(?:n[uú]mero de cr[eé]dito|cr[eé]dito(?: n[uú]mero| numero)?|obligaci[oó]n)\s*(?:es el|es|el|#|:)?\s*(\d{3,})",
    re.I,
)
RE_DOCUMENT = re.compile(
    r"(?:documento(?: de identidad)?|c[eé]dula|\bcc\b)\s*(?:es el|es|el|#|:)?\s*(\d(?:[\d\.]{4,}\d)?)",
    re.I,
)
RE_AMOUNT = re.compile(
    r"\$\s?\d{1,3}(?:\.\d{3})+(?:,\d+)?"          # $185.000
    r"|\$\s?\d{4,}"                               # $95000
    r"|\b\d{1,3}(?:\.\d{3}){1,3}\b"               # 185.000 / 1.020.000
    r"|\b\d{5,7}\b(?!\s*(?:de|del)\b)"            # 250000 (bare)
)
RE_REFERENCE = re.compile(
    r"(?:referencia|ref\.?|n[uú]mero de transacci[oó]n|transacci[oó]n|comprobante)\s*(?:n[uú]mero|#|:)?\s*([A-Za-z]?\d{4,})",
    re.I,
)
RE_DATE = re.compile(
    rf"\b\d{{1,2}} de (?:{MONTHS})\b"
    rf"|\bel (?:{WEEKDAYS})(?: pasado)?\b"
    r"|\bayer\b|\banteayer\b|\bhoy\b|\bma[nñ]ana\b"
    r"|\bhace \d+ (?:d[ií]as|semanas?|mes(?:es)?)\b"
    r"|\bpagu[eé] el \d{1,2}\b",
    re.I,
)
RE_PAYMENT_METHOD = re.compile(
    r"\b(?:PSE|Nequi|Daviplata|Efecty|Baloto|Bancolombia|Davivienda|corresponsal(?:es)? bancarios?|"
    r"transferencia|tarjeta de cr[eé]dito|tarjeta d[eé]bito|tarjeta|efectivo|banco)\b",
    re.I,
)
RE_AGENT = re.compile(r"\b(?:la asesora|el asesor|asesora|asesor)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+|[a-záéíóúñ]{3,})\b")
RE_CARD = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b")


def _first(pattern: re.Pattern, text: str, group: int = 0) -> Optional[str]:
    m = pattern.search(text)
    return m.group(group) if m else None


def extract_entities(text: str) -> Entities:
    masked = [m.group(0) for m in RE_MASKED.finditer(text)]

    credit = _first(RE_CREDIT, text, 1)
    document = _first(RE_DOCUMENT, text, 1)
    if document and any(document in mv for mv in masked):
        document = None  # masked by the customer: keep it only under masked_values

    # amounts: skip numbers that are the credit or document number
    amount = None
    for m in RE_AMOUNT.finditer(text):
        candidate = m.group(0)
        digits = re.sub(r"\D", "", candidate)
        if credit and digits == credit:
            continue
        if document and digits == re.sub(r"\D", "", document):
            continue
        if any(candidate in mv for mv in masked):
            continue
        amount = candidate
        break

    reference = _first(RE_REFERENCE, text, 1)
    if reference and (reference == credit or reference == document):
        reference = None

    method = _first(RE_PAYMENT_METHOD, text)
    if method and method.lower() == "banco" and re.search(r"\bbanco\b", text, re.I) and RE_PAYMENT_METHOD.search(text[RE_PAYMENT_METHOD.search(text).end():]):
        # prefer a named rail over the generic word "banco" when both appear
        later = RE_PAYMENT_METHOD.search(text, RE_PAYMENT_METHOD.search(text).end())
        method = later.group(0) if later else method

    agent = None
    m = RE_AGENT.search(text)
    if m:
        name = m.group(1)
        if name.lower() not in {"humano", "real", "que", "me", "de", "para", "por", "fue", "es", "muy"}:
            agent = name

    entities = Entities(
        credit_number=credit,
        document_number=document,
        amount=amount,
        payment_date=_first(RE_DATE, text),
        transaction_reference=reference,
        payment_method_or_bank=method,
        named_agent=agent,
        masked_values=masked,
    )
    return verify_entities(entities, text)


def verify_entities(entities: Entities, text: str) -> Entities:
    """Drop any value that is not a verbatim substring of the text (case-insensitive for
    method/bank names, exact otherwise). Applied to our extraction and to the model's."""
    data = entities.model_dump()
    for key, value in list(data.items()):
        if key == "masked_values":
            data[key] = [v for v in value if v in text]
        elif value is None:
            continue
        elif key == "payment_method_or_bank":
            if value.lower() not in text.lower():
                data[key] = None
        elif value not in text:
            data[key] = None
    return Entities(**data)


def merge_entities(ours: Entities, theirs: Entities, text: str) -> Entities:
    """Rules first, model second: the model may fill fields the rules left empty, never
    overwrite them. Everything is re-verified against the text."""
    merged = ours.model_dump()
    for key, value in theirs.model_dump().items():
        if key == "masked_values":
            merged[key] = list(dict.fromkeys(merged[key] + value))
        elif merged.get(key) is None and value:
            merged[key] = value
    return verify_entities(Entities(**merged), text)


def pii_present(entities: Entities, text: str) -> bool:
    return entities.document_number is not None or RE_CARD.search(text) is not None
