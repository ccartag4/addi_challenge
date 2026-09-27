"""
Build the gold-set CSV for human labelling (evaluation step).

Selection (deterministic, seed 42): every message the pipeline found hard (model confidence
below 0.70, disagreement with the taxonomy example ids, drafts rejected by the verifier, the
gibberish-with-words case), then a stratified fill by the pipeline's primary reason so that every
reason appears at least twice and the rest is proportional to volume, up to 90 messages.

Pre-labels come from `evidence/gold/prelabels_assistant.json`, written by the assistant reading
the messages (independent of the pipeline, per Anthropic's eval guide: the reference must not be
derived from the model under test). The human confirms or corrects in the `gold_*` columns; an
empty gold cell means "the pre-label is right".

    python scripts/make_gold_set.py --print-texts     # list the selected messages (for pre-labelling)
    python scripts/make_gold_set.py                   # write evidence/gold/gold_set.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "output" / "triage_results.jsonl"
CLASSIFICATIONS = ROOT / "output" / "classifications.jsonl"
GOLD_DIR = ROOT / "evidence" / "gold"
PRELABELS = GOLD_DIR / "prelabels_assistant.json"
OUT = GOLD_DIR / "gold_set.csv"
TAXONOMY = yaml.safe_load((ROOT / "lumo_triage" / "policy" / "taxonomy.yaml").read_text(encoding="utf-8"))

TARGET = 90
MIN_PER_REASON = 2
SEED = 42
ALWAYS = ["MSG-346", "MSG-150"]          # gibberish with words; weather plus a real request


def load_records() -> list[dict]:
    return [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]


def select(records: list[dict]) -> list[str]:
    by_id = {r["id"]: r for r in records}
    expected = {mid: r["id"] for r in TAXONOMY["reasons"] for mid in r.get("examples", [])}
    hard: list[str] = []
    for r in records:
        c = r["classification"]
        if c is None:
            hard.append(r["id"]); continue
        model_classified = "LLM_CLASSIFIED" in r["processing"]["rules_applied"]
        if model_classified and c["confidence"] < 0.70:
            hard.append(r["id"])
        if r["id"] in expected and expected[r["id"]] != c["primary_reason"]:
            hard.append(r["id"])
        if r["draft_reply"].get("rejected_text"):
            hard.append(r["id"])
    chosen: list[str] = []
    for mid in ALWAYS + hard:
        if mid in by_id and mid not in chosen:
            chosen.append(mid)

    rng = random.Random(SEED)
    pools: dict[str, list[str]] = defaultdict(list)
    for r in records:
        reason = r["classification"]["primary_reason"] if r["classification"] else "unclassified"
        if r["id"] not in chosen:
            pools[reason].append(r["id"])
    for ids in pools.values():
        rng.shuffle(ids)
    counts = Counter(r["classification"]["primary_reason"] if r["classification"] else "unclassified" for r in records)
    have = Counter(by_id[m]["classification"]["primary_reason"] if by_id[m]["classification"] else "unclassified" for m in chosen)

    # minimum per reason
    for reason in counts:
        while have[reason] < MIN_PER_REASON and pools[reason]:
            chosen.append(pools[reason].pop()); have[reason] += 1
    # proportional fill
    total = sum(counts.values())
    while len(chosen) < TARGET:
        deficits = sorted(((counts[r] / total) * TARGET - have[r], r) for r in counts if pools[r])
        if not deficits:
            break
        _, reason = deficits[-1]
        chosen.append(pools[reason].pop()); have[reason] += 1
    return chosen[:TARGET]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print-texts", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    records = load_records()
    by_id = {r["id"]: r for r in records}
    chosen = sorted(select(records), key=lambda m: int(m.split("-")[1]))
    # the message texts live in classifications.jsonl (triage_results.jsonl carries no raw text)
    texts = {json.loads(l)["id"]: json.loads(l)["text"] for l in CLASSIFICATIONS.read_text(encoding="utf-8").splitlines() if l.strip()}

    if args.print_texts:
        for mid in chosen:
            print(f"{mid} [{by_id[mid]['channel']}] {texts.get(mid, '')}")
        print(f"\n{len(chosen)} messages selected", file=sys.stderr)
        return

    prelabels = json.loads(PRELABELS.read_text(encoding="utf-8-sig")) if PRELABELS.exists() else {}
    missing = [m for m in chosen if m not in prelabels]
    if missing:
        sys.exit(f"missing pre-labels for {len(missing)} messages: {missing[:10]}")

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "channel", "text",
                    "prelabel_primary_reason", "prelabel_secondary_reasons", "prelabel_priority", "prelabel_action", "prelabel_note",
                    "gold_primary_reason", "gold_secondary_reasons", "gold_priority", "gold_action", "gold_note"])
        for mid in chosen:
            p = prelabels[mid]
            w.writerow([mid, by_id[mid]["channel"], texts[mid], p["reason"], ", ".join(p.get("secondary", [])), p["priority"], p["action"], p.get("note", ""),
                        "", "", "", "", ""])
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} with {len(chosen)} messages")


if __name__ == "__main__":
    main()
