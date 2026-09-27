"""
Tier-0 rules and high-precision flag detectors.

Tier-0 decides, without any model call, the messages that carry no request at all: gibberish,
a bare greeting, a closing "gracias". Everything else goes to the model.

Flag detectors are deliberately conservative regular expressions: a hit is trusted, a miss is
not (the model can still raise the flag). Codes are returned so every decision can list the
rules that fired (`processing.rules_applied`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .normalize import canonical_tokens
from .schema import Flags

GREETING_TOKENS = {"hola", "holaa", "holaaa", "buenas", "buenos", "dias", "tardes", "noches", "buen", "dia", "hey", "que", "tal", "saludos"}
THANKS_TOKENS = {"ok", "oki", "okey", "listo", "vale", "gracias", "muchas", "todo", "bien", "perfecto", "genial", "super", "ya", "quedo", "resuelto", "lo", "de", "ayer", "hoy", "entendido", "dale"}
PRAISE = re.compile(r"amable|excelente|felicit|agradec\w*\s+(?:a|al|la|el)|muy buen[ao]|s[uú]per bien|sigan as[ií]|me ayud[oó]|me atendi[oó]|r[aá]pid[oa]|f[aá]cil de usar|cliente fiel", re.I)
TEST_WORDS = re.compile(r"\b(?:probando|prueba|test|testing|123)\b", re.I)


@dataclass(frozen=True)
class Tier0:
    reason: str          # ruido | saludo_incompleto | sin_accion
    code: str            # rule code for rules_applied


def _looks_gibberish(tokens: list[str]) -> bool:
    if not tokens:
        return True
    vowels = set("aeiou")
    def wordlike(t: str) -> bool:
        if t.isdigit():
            return False
        return any(c in vowels for c in t) and not re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", t)
    words = [t for t in tokens if not t.isdigit()]
    if not words:
        return True
    return sum(1 for t in words if not wordlike(t)) / len(words) >= 0.5


def tier0(text: str) -> Optional[Tier0]:
    tokens = canonical_tokens(text)
    stripped = text.strip()
    # 1. noise: empty, punctuation only, gibberish, "probando"
    if len(stripped) < 3 or not tokens:
        return Tier0("ruido", "T0_EMPTY_OR_PUNCTUATION")
    if TEST_WORDS.search(text) and len(tokens) <= 6:
        return Tier0("ruido", "T0_TEST_MESSAGE")
    if len(tokens) <= 6 and _looks_gibberish(tokens):
        return Tier0("ruido", "T0_GIBBERISH")
    # 2. greeting only
    if len(tokens) <= 4 and set(tokens) <= GREETING_TOKENS:
        return Tier0("saludo_incompleto", "T0_GREETING_ONLY")
    # 3. closing / thanks without a request and without praise (praise is feedback, for the model)
    if len(tokens) <= 9 and set(tokens) <= THANKS_TOKENS | GREETING_TOKENS and "gracias" in tokens or (
        len(tokens) <= 4 and set(tokens) <= THANKS_TOKENS
    ):
        if not PRAISE.search(text):
            return Tier0("sin_accion", "T0_CLOSING_THANKS")
    return None


FLAG_PATTERNS: dict[str, re.Pattern] = {
    "requests_human": re.compile(
        r"(?:asesor|agente|persona|alguien|humano)\s+(?:humano|real|de verdad)|hablar (?:con|directamente con) (?:un asesor|un agente|una persona|alguien|un humano)"
        r"|(?:pasar|comunicar|comuniquen)(?:me)? con (?:un asesor|un agente|alguien|una persona)|no (?:con|quiero) (?:el|al) bot|el bot no|robot no|chat(?:bot| autom[aá]tico) no"
        r"|hay alguien ah[ií]|respuestas autom[aá]ticas|me pasan (?:un|con un) asesor", re.I),
    "fraud_or_security": re.compile(
        r"phishing|estafa|fraude|suplantaci|hackea|clonaron|robaron (?:el|mi) celular|perd[ií] (?:el|mi) celular|me robaron\b"
        r"|no reconozco (?:una|un|esa|ese)|(?:compra|cobro|cr[eé]dito|desembolso) (?:a cuotas )?(?:que|q) (?:yo )?no (?:hice|saqu[eé]|autoric[eé]|ped[ií])"
        r"|usaron mi(?:s datos| identidad)|movimientos raros|mensaje (?:raro|falso|sospechoso)|link raro|sms raro|correo sospechoso", re.I),
    "legal_threat": re.compile(r"superintendencia|abogad[oa]|demanda|denunci|defensor[ií]a del consumidor|acci[oó]n legal", re.I),
    "collections_harassment": re.compile(r"\bacoso\b|me llaman (?:todo el d[ií]a|todos los d[ií]as|a toda hora)|llamando a mis familiares|dejen de llamar|tanto(?:s)? (?:llamada|mensaje)s? de cobranza", re.I),
    "vulnerable_customer": re.compile(r"sin (?:trabajo|empleo)|perd[ií] (?:el|mi) trabajo|me qued[eé] sin (?:trabajo|empleo)|hospitaliz|estoy enferm[oa]|gastos m[eé]dicos|mi (?:mam[aá]|pap[aá]|hij[oa]) est[aá] (?:hospitaliz|enferm)|situaci[oó]n (?:econ[oó]mica )?(?:dif[ií]cil|complicada)", re.I),
    "imminent_deadline": re.compile(r"vence ma[nñ]ana|ma[nñ]ana (?:se )?vence|se vence ma[nñ]ana|hoy (?:se )?vence|por ser reportad|(?:no|nunca) (?:quiero|vayan a) (?:q(?:ue)? )?me reporten|antes de que me reporten", re.I),
    "repeat_contact": re.compile(r"tercera vez|segunda vez|cuarta vez|otra vez (?:escribo|les escribo)|llevo \d+ (?:d[ií]as|semanas) (?:llamando|escribiendo|esperando)|desde hace \d+ d[ií]as y nada|nadie me (?:resuelve|responde|contesta)|ya (?:hab[ií]a )?escrit[oa]", re.I),
    "prompt_injection_suspected": re.compile(
        r"ignor[ae] (?:las|tus|todas las) (?:instrucciones|reglas)|olvida (?:las|tus) (?:reglas|instrucciones)|act[uú]a como|eres (?:ahora )?un[a]? (?:asistente|modelo|ia)|system prompt|prompt del sistema"
        r"|revela (?:tu|el) prompt|muestra (?:tu|el) prompt|jailbreak|responde (?:solo )?con tu configuraci[oó]n|instrucci[oó]n del sistema|developer mode|modo desarrollador", re.I),
}


def detect_flags(text: str) -> tuple[Flags, list[str]]:
    hits = {name: bool(p.search(text)) for name, p in FLAG_PATTERNS.items()}
    codes = [f"FLAG_{name.upper()}" for name, hit in hits.items() if hit]
    return Flags(**hits), codes
