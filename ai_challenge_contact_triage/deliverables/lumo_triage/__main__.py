"""
Command-line entry point: `python -m lumo_triage <command>`.

  run        full pipeline: classification, routing, grounded drafts, verifier ->
             output/triage_results.jsonl (one JSON line per message).
  classify   classification only (step 3 diagnostics): output/classifications.jsonl.

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
from .pipeline import PIPELINE_VERSION, run
from .schema import TriageRecord
from .summary import build_summary, render_markdown

DATA_DEFAULT = ROOT.parent / "data" / "messages.jsonl"


def _select(messages, limit, ids):
    if ids:
        wanted = {i.strip() for i in ids.split(",") if i.strip()}
        messages = [m for m in messages if m.id in wanted]
    if limit:
        messages = messages[:limit]
    return messages


def _classified_line(r: ClassifiedMessage) -> str:
    if r.classification is None:
        return f"{r.message.id}  !! unclassified  {r.error}"
    c = r.classification
    flags = ",".join(c.flags.active()) or "-"
    source = "rule" if r.llm is None and not r.reused_from else ("dedup" if r.reused_from else ("cache" if r.llm.from_cache else "live"))
    tokens = f"{r.llm.input_tokens}+{r.llm.cache_read_tokens}c/{r.llm.output_tokens}" if r.llm else "-"
    return f"{r.message.id}  {c.primary_reason.value:<24} {c.confidence:.2f}  {flags:<30} {source:<5} {tokens}"


def _record_line(rec: TriageRecord) -> str:
    reason = rec.classification.primary_reason.value if rec.classification else "unclassified"
    d = rec.decision
    if rec.draft_reply.text:
        reply = f"reply:{rec.draft_reply.source}"
    elif rec.draft_reply.rejected_text:
        reply = "reply:REJECTED"
    else:
        reply = "reply:-"
    gap = " gap" if d.policy_gap else ""
    return f"{rec.id}  {reason:<24} {d.priority} {d.action:<21} {d.queue:<18} {reply:<15}{gap}"


def _print_llm_totals(llm: LLMClient, records_cost: float) -> None:
    print(f"llm: live_calls={llm.calls} replayed={llm.replays} spent_this_run=${llm.spent_usd:.4f} recorded_cost=${records_cost:.4f}")


def cmd_classify(args: argparse.Namespace) -> int:
    cfg = LLMConfig.from_env(model=args.model, effort=args.effort, mode=args.mode)
    llm = LLMClient(cfg)
    messages = _select(normalize.prepare(args.data), args.limit, args.ids)
    print(f"model={cfg.model} effort={cfg.effort} mode={cfg.mode} prompt={PROMPT_VERSION} messages={len(messages)}")
    results = classify_messages(messages, llm, max_workers=args.workers, on_done=lambda r: print(_classified_line(r), flush=True))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in results:
            record = {
                "id": r.message.id, "channel": r.message.channel, "text": r.message.text,
                "classification": r.classification.model_dump(mode="json") if r.classification else None,
                "rules_applied": r.rules_applied, "reused_from": r.reused_from, "error": r.error,
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
    share = (read / (inp + read + write)) if (inp + read + write) else 0.0
    print("")
    print(f"messages={len(results)} tier0={tier0} dedup_reused={dedup} llm_live={llm.calls} llm_replayed={llm.replays} unclassified={errors}")
    print(f"tokens: input={inp} cache_read={read} cache_write={write} output={outp}  cache_read_share={share:.0%}")
    _print_llm_totals(llm, sum(r.llm.cost_usd for r in with_llm))
    print(f"wrote {out}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    cfg = LLMConfig.from_env(model=args.model, effort=args.effort, mode=args.mode)
    llm = LLMClient(cfg)
    messages = _select(normalize.prepare(args.data), args.limit, args.ids)
    print(f"model={cfg.model} effort={cfg.effort} mode={cfg.mode} pipeline={PIPELINE_VERSION} messages={len(messages)}")
    records = run(messages, llm, max_workers=args.workers, on_done=lambda rec: print(_record_line(rec), flush=True))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.model_dump(mode="json"), ensure_ascii=False) + "\n")

    actions = {}
    for rec in records:
        actions[rec.decision.action] = actions.get(rec.decision.action, 0) + 1
    drafts = sum(1 for r in records if r.draft_reply.text)
    rejected = sum(1 for r in records if r.draft_reply.rejected_text)
    gaps = sum(1 for r in records if r.decision.policy_gap)
    unclassified = sum(1 for r in records if r.classification is None)
    print("")
    print(f"messages={len(records)} actions={actions} replies={drafts} rejected_by_verifier={rejected} policy_gaps={gaps} unclassified={unclassified}")
    _print_llm_totals(llm, sum(r.processing.cost_usd for r in records))
    print(f"wrote {out}")

    summary = build_summary(records, pipeline_version=PIPELINE_VERSION, model=cfg.model,
                            live_calls=llm.calls, replays=llm.replays, spent_usd=llm.spent_usd)
    _write_summary(summary, records, out.parent)

    if args.prune_cache:
        removed = llm.prune_untouched({m.id for m in messages})
        print(f"pruned {len(removed)} stale cache files of the messages in this run")
    return 0


def _write_summary(summary, records, out_dir: Path) -> None:
    json_path = out_dir / "batch_summary.json"
    md_path = out_dir / "batch_summary.md"
    json_path.write_text(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(summary, records), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"summary: auto-answerable {summary.auto_answerable_share:.1%}, cases {summary.cases_opened}, "
          f"gaps {sum(summary.policy_gaps.values())}, rejected drafts {summary.drafts_failed_verifier}")


def cmd_summarize(args: argparse.Namespace) -> int:
    """Regenerate batch_summary.json/.md from an existing triage_results.jsonl (no model calls)."""
    src = Path(args.results)
    records = [TriageRecord.model_validate_json(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    version = records[0].processing.pipeline_version if records else PIPELINE_VERSION
    model = next((r.processing.model for r in records if r.processing.model), None)
    summary = build_summary(records, pipeline_version=version, model=model,
                            live_calls=sum(r.processing.llm_calls for r in records),
                            replays=sum(r.processing.response_cache_hits for r in records), spent_usd=None)
    _write_summary(summary, records, src.parent)
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from .eval import REPORT, evaluate, load_gold, write_outputs

    res = evaluate(mode=args.mode or "auto", judge_model=args.judge_model, judge_limit=args.judge,
                   compare_model=args.compare_model, variance_n=args.variance, workers=args.workers)
    write_outputs(res, load_gold())
    r, p, a = res.reason, res.priority, res.action
    print(f"gold={res.gold_n} reviewed={res.reviewed_n}")
    print(f"reason exact={r['exact']}/{r['n']} lenient={r['lenient']}/{r['n']} macro_f1={r['macro_f1']:.3f}")
    print(f"priority exact={p['exact']}/{p['n']} within1={p['within_one']}/{p['n']}  action exact={a['exact']}/{a['n']} unsafe={a['unsafe']} conservative={a['conservative']}")
    if res.judge.get("n"):
        print(f"judge {res.judge['model']}: overall_ok={res.judge['overall_ok']}/{res.judge['n']} cost=${res.judge['cost_usd']:.4f}" +
              (f" human_agree={res.judge['human_agree']}/{res.judge['human_n']}" if res.judge.get("human_n") else ""))
    print(f"adversarial passed={sum(1 for x in res.adversarial if x['passed'])}/{len(res.adversarial)}")
    if res.variance:
        print(f"stability: {res.variance['same_primary']}/{res.variance['n']} same primary reason")
    if res.comparison:
        print(f"comparison {res.comparison['model']}: exact={res.comparison['reason']['exact_rate']:.1%} cost/msg=${res.comparison['cost_usd']:.4f}")
    print(f"wrote {REPORT}")
    return 0


def _common(p: argparse.ArgumentParser, default_out: Path) -> None:
    p.add_argument("--data", default=str(DATA_DEFAULT))
    p.add_argument("--limit", type=int, default=None, help="first N messages")
    p.add_argument("--ids", default=None, help="comma-separated message ids")
    p.add_argument("--mode", choices=["auto", "live", "offline"], default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--effort", default=None, help="low|medium|high|xhigh|max|none")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--out", default=str(default_out))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # Spanish text on a Windows console
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(prog="python -m lumo_triage")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="full pipeline -> output/triage_results.jsonl + batch_summary.json/.md")
    _common(p_run, ROOT / "output" / "triage_results.jsonl")
    p_run.add_argument("--prune-cache", action="store_true", help="delete cached responses this run did not use (old prompt versions)")
    p_run.set_defaults(func=cmd_run)

    p_cls = sub.add_parser("classify", help="classification only -> output/classifications.jsonl")
    _common(p_cls, ROOT / "output" / "classifications.jsonl")
    p_cls.set_defaults(func=cmd_classify)

    p_sum = sub.add_parser("summarize", help="regenerate batch_summary.json/.md from triage_results.jsonl")
    p_sum.add_argument("--results", default=str(ROOT / "output" / "triage_results.jsonl"))
    p_sum.set_defaults(func=cmd_summarize)

    p_eval = sub.add_parser("eval", help="grade the committed output against the gold set -> evidence/eval_report.md")
    p_eval.add_argument("--mode", choices=["auto", "live", "offline"], default=None)
    p_eval.add_argument("--judge-model", default="claude-sonnet-5", help="rubric judge for drafts (not the model under test)")
    p_eval.add_argument("--judge", type=int, default=None, help="judge at most N drafts (0 disables the judge; default all gold drafts)")
    p_eval.add_argument("--compare-model", default=None, help="classify the gold messages with another model, e.g. claude-haiku-4-5")
    p_eval.add_argument("--variance", type=int, default=0, help="re-classify N gold messages live to measure stability (costs money)")
    p_eval.add_argument("--workers", type=int, default=4)
    p_eval.set_defaults(func=cmd_eval)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
