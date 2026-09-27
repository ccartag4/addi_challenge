"""
Build the draft-review CSV: 20 model drafts from the gold-set messages for a human verdict.
The verdicts calibrate the LLM judge used in the evaluation (agreement between the human and
the judge on the same 20 drafts is reported).

    python scripts/make_draft_review.py      # writes evidence/gold/draft_review.csv
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "output" / "triage_results.jsonl"
CLASSIFICATIONS = ROOT / "output" / "classifications.jsonl"
GOLD = ROOT / "evidence" / "gold" / "gold_set.csv"
OUT = ROOT / "evidence" / "gold" / "draft_review.csv"
TARGET = 20
MAX_PER_REASON = 2


def main() -> None:
    records = {json.loads(l)["id"]: json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()}
    texts = {json.loads(l)["id"]: json.loads(l)["text"] for l in CLASSIFICATIONS.read_text(encoding="utf-8").splitlines() if l.strip()}
    with open(GOLD, encoding="utf-8-sig", newline="") as f:
        gold_ids = [row["id"] for row in csv.DictReader(f)]

    per_reason: Counter = Counter()
    chosen: list[str] = []
    for mid in gold_ids:                                     # gold order is by id: deterministic
        r = records[mid]
        d = r["draft_reply"]
        if d["source"] != "llm" or not d["text"]:
            continue
        reason = r["classification"]["primary_reason"]
        if per_reason[reason] >= MAX_PER_REASON:
            continue
        chosen.append(mid)
        per_reason[reason] += 1
        if len(chosen) == TARGET:
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "primary_reason", "customer_message", "draft_reply", "kb_citations",
                    "verdict (ok | not_ok)", "issue (grounding | wrong_answer | promise | tone | incomplete | other)", "note"])
        for mid in chosen:
            r = records[mid]
            w.writerow([mid, r["classification"]["primary_reason"], texts[mid], r["draft_reply"]["text"],
                        "; ".join(r["draft_reply"]["kb_citations"]), "", "", ""])
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} with {len(chosen)} drafts")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    main()
