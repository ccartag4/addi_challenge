"""
Profile the incoming messages and write the findings as Markdown evidence.

Counts what the design has to handle: channels, timestamp shapes, exact and near duplicates,
sensitive-data patterns, multi-intent markers, risk signals, taxonomy gaps and a rough
keyword bucketing (planning aid only; the model does the real classification).

Usage (from deliverables/):
    python scripts/profile_messages.py --input ../data/messages.jsonl --out evidence/message_profiling.md
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

PATTERNS = {
    "credit number mentioned": r"cr[eé]dito (n[uú]mero |numero )?\d{3,}|credito \d{3,}|n[uú]mero de cr[eé]dito \d+",
    "document number mentioned": r"documento (es )?(el )?\d{6,}|documento \d|cc \d|\b\d{10}\b",
    "masked identifier (xx / XXX)": r"\d\.?[0-9x]*x{2,}|X{3}",
    "amount mentioned": r"\$\s?\d|\b\d{1,3}\.\d{3}\b|\b\d{5,7}\b(?! ?\d)|\d+ ?mil\b",
    "transaction / reference mentioned": r"\bref(erencia)?\.? ?\w*\d|transacci[oó]n \w+",
    "explicit date mentioned": r"\b\d{1,2} de \w+|\bel (lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b|\bayer\b|\bhace \d+ d[ií]as",
    "bank / payment rail named": r"bancolombia|nequi|daviplata|efecty|baloto|pse\b|corresponsal|transferencia",
    "multi-intent markers": r"\by de paso\b|adem[aá]s|tambi[eé]n|\bdos cosas|\btres cosas|\b1\)|\bvarias cosas|aprovecho",
    "urgency words": r"urgente|ya mismo|!!|inmediat",
    "fraud / security signals": r"fraude|robaron|hackear|suplantaci|phishing|estafa|clonaron|no reconozco|perd[ií] mi celular|movimientos raros",
    "legal / regulatory threat or harassment": r"superintendencia|acoso|habeas|borren mis datos|qu[eé] datos m[ií]os",
    "hardship / vulnerability": r"sin trabajo|sin empleo|hospital|enferm|no puedo pagar|no me alcanza|situaci[oó]n (econ[oó]mica )?(dif[ií]cil|complicada)|pr[oó]rroga",
    "asks for a human": r"asesor humano|persona real|agente|humano|alguien ah[ií]|con alguien",
    "out of scope / other business": r"celular(es)?\b|iphone|rappi|pizzer|clima|francia|\bclaro\b|domicilio|parqueadero|seguros? de veh|hipotecari|carros|cuentas de ahorro",
    "credit-bureau terms": r"datacr[eé]dito|cifin|centrales|report",
    "certificates / statements": r"certificad|extracto|paz y salvo|retenci[oó]n|tributario",
    "password mentioned (KB: login is document + OTP)": r"contrase[nñ]a|clave",
    "address change (not in KB)": r"direcci[oó]n",
    "application status (not in taxonomy)": r"solicitud de cr[eé]dito|estado de mi solicitud",
    "interest / fee dispute (not in taxonomy)": r"tasa de inter[eé]s|cuota de manejo|intereses (excesivos|muy altos|abusiv)|cobro (adicional|extra)|seguro q",
    "prepayment / early settlement (not in taxonomy)": r"adelantar|pagar (la totalidad|todo el cr[eé]dito|todo de una)|pago anticipado|saldar|abono a capital",
    "greeting / thanks only or gibberish": r"^(hola|buenas|ok gracias|todo bien gracias.*|gracias.*|\?+|\.\.\.|asd\w*.*|ggg .*|aksjd.*|hola\?\?.*)$",
    "mojibake (encoding)": r"Ã",
}

BUCKETS = [
    ("fraude_seguridad", r"fraude|robaron|hackear|suplantaci|phishing|estafa|clonaron|no reconozco|perd[ií] mi celular|movimientos raros"),
    ("hablar_con_humano", r"asesor humano|persona real|agente real|con un agente|humano|alguien ah[ií]|con alguien|robot"),
    ("queja_reclamo", r"queja|reclamo|p[eé]simo|pqr|supervisor|acoso|superintendencia"),
    ("reporte_centrales", r"datacr[eé]dito|cifin|centrales|report"),
    ("pago_no_aplicado", r"no (se )?(refleja|aplic)|aparece pendiente|dos veces|doble|no me lo han abonado|no aparece"),
    ("no_puede_pagar", r"no (voy a )?pod(er|r[eé]) pagar|no me alcanza|sin trabajo|sin empleo|hospital|enferm|pr[oó]rroga|la mitad"),
    ("refinanciacion_acuerdo", r"refinanci|acuerdo|reestructur|plan de pagos"),
    ("pago_anticipado", r"adelantar|pagar (la totalidad|todo el cr[eé]dito|todo de una)|pago anticipado|saldar|abono a capital"),
    ("intereses_y_cargos", r"tasa de inter[eé]s|cuota de manejo|cobro (adicional|extra)|seguro q|subi[oó] un mont[oó]n|abusivo"),
    ("mora_intereses", r"mora|inter[eé]s"),
    ("fecha_de_pago", r"fecha|vence|cu[aá]ndo (me toca|se vence|es el pago)|d[ií]a me toca"),
    ("metodos_de_pago", r"m[eé]todos? de pago|d[oó]nde (puedo )?pag|c[oó]mo (hago para )?pag|efecty|nequi|baloto|corresponsal|medios de pago|transferencia|link de pago|tarjeta de cr[eé]dito de otro"),
    ("cuenta_y_app", r"\bapp\b|c[oó]digo|otp|bloquead|iniciar sesi[oó]n|contrase[nñ]a|sesi[oó]n|clave"),
    ("datos_personales", r"actualizar|cambi(ar|e) (mi |el )?(n[uú]mero|correo|celular|direcci)|direcci[oó]n|datos personales|datos de contacto"),
    ("certificados_extractos", r"certificad|extracto|paz y salvo|retenci[oó]n|tributario"),
    ("cancelacion", r"cancelar|cerrar (mi )?(cuenta|cr[eé]dito)|cancelaci[oó]n"),
    ("consulta_saldo_cuotas", r"saldo|cu[aá]nto debo|cu[aá]ntas cuotas|cuotas me faltan|valor de la (pr[oó]xima )?cuota|llevo pagad"),
    ("felicitacion_feedback", r"felicit|agradec|gracias|excelente|super amable|muy buena"),
    ("informacion_general", r"horario|abiertos|festivos|n[uú]mero de la l[ií]nea|l[ií]nea de atenci[oó]n|sucursal"),
    ("fuera_de_alcance", r"celular(es)?\b|iphone|rappi|pizzer|clima|francia|\bclaro\b|domicilio|parqueadero|seguros? de veh|hipotecari|carros"),
]


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=str(PROJECT / ".." / "data" / "messages.jsonl"))
    ap.add_argument("--out", default="evidence/message_profiling.md")
    args = ap.parse_args()

    msgs = [json.loads(l) for l in Path(args.input).read_text(encoding="utf-8").splitlines() if l.strip()]
    n = len(msgs)
    pct = lambda x: f"{x} ({100 * x / n:.0f} %)"
    lines = [
        "# Message profiling — data/messages.jsonl",
        "",
        f"Generated {dt.datetime.now():%Y-%m-%d %H:%M} by `scripts/profile_messages.py`. {n} messages.",
        "",
        "## Shape",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Channels | {dict(collections.Counter(m['channel'] for m in msgs))} |",
        f"| Timestamp shapes | {dict(collections.Counter(re.sub(r'[0-9]', '9', m['received_at']) for m in msgs))} |",
        f"| Date range | {min(m['received_at'][:10] for m in msgs)} .. {max(m['received_at'][:10] for m in msgs)} |",
        f"| Sender shapes | {dict(collections.Counter(('phone' if m['from'].startswith('+') else 'client_id' if m['from'].startswith('cliente_') else 'email') for m in msgs))} |",
    ]
    lens = sorted(len(m["text"]) for m in msgs)
    lines.append(f"| Text length min / median / p90 / max | {lens[0]} / {lens[n // 2]} / {lens[int(n * .9)]} / {lens[-1]} |")
    texts = [norm(m["text"]) for m in msgs]
    exact = collections.Counter(texts)
    lines.append(f"| Exact duplicate texts (normalised) | {sum(c - 1 for c in exact.values() if c > 1)} in {sum(1 for c in exact.values() if c > 1)} groups |")
    toks = [set(t.split()) for t in texts]
    pairs, near = 0, set()
    for i in range(n):
        for j in range(i + 1, n):
            a, b = toks[i], toks[j]
            if a and b and len(a & b) / len(a | b) >= 0.6:
                pairs += 1
                near.update((i, j))
    lines.append(f"| Near-duplicate pairs (token Jaccard >= 0.6) | {pairs} pairs, {pct(len(near))} messages involved |")

    lines += ["", "## Signals (regex over the raw text; a message can hit several)", "", "| Signal | Messages | Example |", "|---|---:|---|"]
    for name, pat in PATTERNS.items():
        hits = [m for m in msgs if re.search(pat, m["text"], re.I)]
        lines.append(f"| {name} | {pct(len(hits))} | {hits[0]['id'] if hits else '-'} |")
    caps = [m for m in msgs if sum(c.isupper() for c in m["text"]) > 0.5 * max(1, sum(c.isalpha() for c in m["text"]))]
    lines.append(f"| ALL-CAPS heavy | {pct(len(caps))} | {caps[0]['id'] if caps else '-'} |")

    lines += ["", "## Rough keyword bucketing (planning aid only, first match wins)", "", "| Bucket | Messages |", "|---|---:|"]
    cnt, unmatched = collections.Counter(), []
    for m in msgs:
        for name, pat in BUCKETS:
            if re.search(pat, m["text"], re.I):
                cnt[name] += 1
                break
        else:
            cnt["(no keyword match)"] += 1
            unmatched.append(f"{m['id']}: {m['text'][:70]}")
    for k, v in cnt.most_common():
        lines.append(f"| {k} | {v} |")
    lines += ["", "Unmatched sample (why rules alone cannot classify):", ""] + [f"- {u}" for u in unmatched[:12]]

    out = PROJECT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{n} messages profiled. Wrote {out.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
