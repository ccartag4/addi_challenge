"""
Command-line entry point: `python -m lumo_triage <command>`.

  classify   classification only (step 3): writes output/classifications.jsonl and prints a
             per-message line plus token / cache / cost totals.

Runs from `deliverables/`; the data file is ../data/messages.jsonl unless --data is given.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import normalize
from .classify import PROMPT_VERSION, ClassifiedMessage, classify_messages
from .llm import ROOT, LLMClient, LLMConfig

DATA_DEFAULT = ROOT.parent / "data" / "messages.jsonl"


def _select(messages, limit, ids):
    if ids:
        wanted = {i.strip() for i in ids.split(",") if i.strip()}
        messages = [m for m in messages if m.id in wanted]
    if limit:
        messages = messages[:limit]
    return messages


def _line(r: ClassifiedMessage) -> str:
    if r.classification is None:
        return f"{r.message.id}  !! unclassified  {r.error}"
    c = r.classification
    flags = ",".join(c.flags.active()) or "-"
    source = "rule" if r.llm is None and not r.reused_from else ("dedup" if r.reused_from else ("cache" if r.llm.from_cache else "live"))
    tokens = f"{r.llm.input_tokens}+{r.llm.cache_read_tokens}c/{r.llm.output_tokens}" if r.llm else "-"
    return f"{r.message.id}  {c.primary_reason.value:<24} {c.confidence:.2f}  {flags:<30} {source:<5} {tokens}"


def cmd_classify(args: argparse.Namespace) -> int:
    cfg = LLMConfig.from_env(model=args.model, effort=args.effort, mode=args.mode)
    llm = LLMClient(cfg)
    messages = _select(normalize.prepare(args.data), args.limit, args.ids)
    print(f"model={cfg.model} effort={cfg.effort} mode={cfg.mode} prompt={PROMPT_VERSION} messages={len(messages)}")

    results = classify_messages(messages, llm, max_workers=args.workers, on_done=lambda r: print(_line(r), flush=True))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in results:
            record = {
                "id": r.message.id,
                "channel": r.message.channel,
                "text": r.message.text,
                "classification": r.classification.model_dump(mode="json") if r.classification else None,
                "rules_applied": r.rules_applied,
                "reused_from": r.reused_from,
                "error": r.error,
                "llm": None if r.llm is None else {
                    "served_by": r.llm.served_by, "from_cache": r.llm.from_cache, "stop_reason": r.llm.stop_reason,
                    "input_tokens": r.llm.input_tokens, "cache_read_tokens": r.llm.cache_read_tokens,
                    "cache_write_tokens": r.llm.cache_write_tokens, "output_tokens": r.llm.output_tokens,
                    "latency_ms": r.llm.latency_ms, "cost_usd": round(r.llm.cost_usd, 6),
                },
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with_llm = [r for r in results if r.llm is not None]
    tier0 = sum(1 for r in results if r.llm is None and r.reused_from is None and r.classification is not None)
    dedup = sum(1 for r in results if r.reused_from)
    errors = sum(1 for r in results if r.classification is None)
    inp = sum(r.llm.input_tokens for r in with_llm)
    read = sum(r.llm.cache_read_tokens for r in with_llm)
    write = sum(r.llm.cache_write_tokens for r in with_llm)
    outp = sum(r.llm.output_tokens for r in with_llm)
    recorded = sum(r.llm.cost_usd for r in with_llm)
    prompt_tokens = inp + read + write
    share = (read / prompt_tokens) if prompt_tokens else 0.0
    print("")
    print(f"messages={len(results)} tier0={tier0} dedup_reused={dedup} llm_live={llm.calls} llm_replayed={llm.replays} unclassified={errors}")
    print(f"tokens: input={inp} cache_read={read} cache_write={write} output={outp}  cache_read_share={share:.0%}")
    print(f"cost: recorded=${recorded:.4f} spent_this_run=${llm.spent_usd:.4f}")
    print(f"wrote {out}")
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # Spanish text on a Windows console
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(prog="python -m lumo_triage")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("classify", help="classify messages (no routing, no drafts)")
    p.add_argument("--data", default=str(DATA_DEFAULT))
    p.add_argument("--limit", type=int, default=None, help="first N messages")
    p.add_argument("--ids", default=None, help="comma-separated message ids")
    p.add_argument("--mode", choices=["auto", "live", "offline"], default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--effort", default=None, help="low|medium|high|xhigh|max|none")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--out", default=str(ROOT / "output" / "classifications.jsonl"))
    p.set_defaults(func=cmd_classify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
