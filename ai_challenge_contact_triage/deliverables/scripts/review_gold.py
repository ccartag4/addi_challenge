"""
Terminal reviewer for the gold set and the draft review, so nobody has to fight Excel and CSV
encodings. Shows one item at a time, saves after every answer (safe to stop and resume).

    python scripts/review_gold.py             # gold_set.csv: reason / priority / action per message
    python scripts/review_gold.py --drafts    # draft_review.csv: ok / not_ok per draft

Gold set answers:
    Enter                     agree with the pre-label (writes "ok" in gold_note)
    r=<reason>                correct the primary reason (taxonomy id)
    p=<P0..P4>                correct the priority
    a=<action>                correct the action
    s=<reason,reason>         set the secondary reasons
    n=<free text>             add a note (kept with the row)
    several at once:          r=queja_reclamo p=P1 n=formal complaint
    ?                         list the valid reasons, priorities and actions
    b                         go back one row
    q                         save and quit

Draft answers:
    Enter                     the draft could be sent as is ("ok")
    x=<issue> [note]          not ok; issue is one of grounding, wrong_answer, promise, tone, incomplete, other
    b / q                     back / save and quit
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "evidence" / "gold" / "gold_set.csv"
DRAFTS = ROOT / "evidence" / "gold" / "draft_review.csv"
TAXONOMY = yaml.safe_load((ROOT / "lumo_triage" / "policy" / "taxonomy.yaml").read_text(encoding="utf-8"))
REASONS = [r["id"] for r in TAXONOMY["reasons"]]
PRIORITIES = list(TAXONOMY["priorities"].keys())
ACTIONS = ["auto_reply", "auto_reply_and_route", "route_to_human", "close_no_reply"]
ISSUES = ["grounding", "wrong_answer", "promise", "tone", "incomplete", "other"]
WIDTH = min(110, shutil.get_terminal_size((110, 40)).columns - 2)


def load(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(r) for r in reader]


def save(path: Path, fields: list[str], rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def ask(prompt: str = "\n  > ") -> str:
    """input() with a byte-order mark and surrounding whitespace removed (piped stdin on
    Windows may start with a BOM)."""
    try:
        return input(prompt).strip().lstrip("﻿").strip()
    except EOFError:
        return "q"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def wrap(text: str, indent: str = "    ") -> str:
    return "\n".join(textwrap.wrap(text, WIDTH - len(indent), initial_indent=indent, subsequent_indent=indent)) or indent


def reviewed_gold(r: dict) -> bool:
    return any((r.get(k) or "").strip() for k in ("gold_primary_reason", "gold_secondary_reasons", "gold_priority", "gold_action")) \
        or (r.get("gold_note") or "").strip().lower().startswith("ok")


def show_help() -> None:
    print("\n  reasons:   " + ", ".join(REASONS))
    print("  priorities: " + ", ".join(f"{p} ({TAXONOMY['priorities'][p]['label']}, {TAXONOMY['priorities'][p]['description']})" for p in PRIORITIES))
    print("  actions:   " + ", ".join(ACTIONS) + "\n")


def parse_gold_answer(answer: str, row: dict) -> str | None:
    """Apply an answer to the row. Returns an error message or None."""
    tokens = answer.split()
    note_parts: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("n="):
            note_parts.append(" ".join([tok[2:]] + tokens[i + 1:]))
            break
        key, _, value = tok.partition("=")
        if not value:
            return f"could not read {tok!r}; use r=, p=, a=, s=, n= or ? for help"
        if key == "r":
            if value not in REASONS:
                return f"unknown reason {value!r} (type ? to list them)"
            row["gold_primary_reason"] = value
        elif key == "p":
            value = value.upper()
            if value not in PRIORITIES:
                return f"priority must be one of {PRIORITIES}"
            row["gold_priority"] = value
        elif key == "a":
            if value not in ACTIONS:
                return f"action must be one of {ACTIONS}"
            row["gold_action"] = value
        elif key == "s":
            items = [s for s in value.replace(";", ",").split(",") if s]
            bad = [s for s in items if s not in REASONS]
            if bad:
                return f"unknown secondary reason(s) {bad}"
            row["gold_secondary_reasons"] = ", ".join(items)
        else:
            return f"unknown key {key!r}; use r=, p=, a=, s=, n="
        i += 1
    if note_parts:
        row["gold_note"] = note_parts[0]
    elif not (row.get("gold_note") or "").strip():
        row["gold_note"] = "corrected"
    return None


def review_gold(path: Path) -> None:
    fields, rows = load(path)
    pending = [i for i, r in enumerate(rows) if not reviewed_gold(r)]
    print(f"{len(rows)} messages, {len(rows) - len(pending)} already reviewed, {len(pending)} to go. Enter = agree, ? = help, q = save and quit.\n")
    pos = 0
    order = pending
    while pos < len(order):
        i = order[pos]
        r = rows[i]
        print("=" * WIDTH)
        print(f"[{pos + 1}/{len(order)}] {r['id']}  ({r['channel']})")
        print(wrap(r["text"]))
        sec = f"  secondary: {r.get('prelabel_secondary_reasons')}" if (r.get("prelabel_secondary_reasons") or "").strip() else ""
        print(f"\n    pre-label: {r['prelabel_primary_reason']}  |  {r['prelabel_priority']}  |  {r['prelabel_action']}{sec}")
        if (r.get("prelabel_note") or "").strip():
            print(wrap("note: " + r["prelabel_note"], indent="    "))
        answer = ask()
        if answer == "q":
            break
        if answer == "?":
            show_help()
            continue
        if answer == "b":
            pos = max(0, pos - 1)
            continue
        if answer == "":
            for k in ("gold_primary_reason", "gold_secondary_reasons", "gold_priority", "gold_action"):
                r[k] = ""
            r["gold_note"] = "ok"
        else:
            err = parse_gold_answer(answer, r)
            if err:
                print("  !! " + err)
                continue
        save(path, fields, rows)
        pos += 1
    save(path, fields, rows)
    done = sum(1 for r in rows if reviewed_gold(r))
    print(f"\nsaved {rel(path)}: {done}/{len(rows)} reviewed.")


def review_drafts(path: Path) -> None:
    fields, rows = load(path)
    verdict_col = next(f for f in fields if f.startswith("verdict"))
    issue_col = next(f for f in fields if f.startswith("issue"))
    pending = [i for i, r in enumerate(rows) if not (r.get(verdict_col) or "").strip()]
    print(f"{len(rows)} drafts, {len(rows) - len(pending)} already reviewed, {len(pending)} to go. Enter = ok, x=<issue> [note] = not ok, q = save and quit.\n")
    pos = 0
    while pos < len(pending):
        i = pending[pos]
        r = rows[i]
        print("=" * WIDTH)
        print(f"[{pos + 1}/{len(pending)}] {r['id']}  reason: {r['primary_reason']}  cites: {r['kb_citations']}")
        print("  CUSTOMER:")
        print(wrap(r["customer_message"]))
        print("  DRAFT:")
        print(wrap(r["draft_reply"]))
        answer = ask()
        if answer == "q":
            break
        if answer == "b":
            pos = max(0, pos - 1)
            continue
        if answer == "":
            r[verdict_col], r[issue_col] = "ok", ""
        elif answer.startswith("x="):
            issue, _, note = answer[2:].partition(" ")
            if issue not in ISSUES:
                print(f"  !! issue must be one of {ISSUES}")
                continue
            r[verdict_col], r[issue_col] = "not_ok", issue
            if note:
                r["note"] = note
        else:
            print("  !! Enter for ok, x=<issue> [note] for not ok, b back, q quit")
            continue
        save(path, fields, rows)
        pos += 1
    save(path, fields, rows)
    done = sum(1 for r in rows if (r.get(verdict_col) or "").strip())
    print(f"\nsaved {rel(path)}: {done}/{len(rows)} reviewed.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", action="store_true", help="review draft_review.csv instead of gold_set.csv")
    ap.add_argument("--csv", default=None, help="review another CSV file (tests)")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if args.drafts:
        review_drafts(Path(args.csv) if args.csv else DRAFTS)
    else:
        review_gold(Path(args.csv) if args.csv else GOLD)


if __name__ == "__main__":
    main()
