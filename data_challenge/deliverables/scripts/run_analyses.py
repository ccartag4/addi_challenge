"""
Run compiled dbt analyses against the local DuckDB warehouse and write the full results as
Markdown tables. `dbt show` truncates cell values, so it cannot serve as evidence; this script
can.

Usage (from deliverables/, after `dbt compile --select "<pattern>"`):

    python scripts/run_analyses.py --pattern "dq_*" --out evidence/bronze_profiling.md
    python scripts/run_analyses.py --pattern "q0*"  --out evidence/results.md

The warehouse is opened read-only, so the script never modifies data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import sys
from pathlib import Path

import duckdb

PROJECT_DIR = Path(__file__).resolve().parents[1]
COMPILED_ANALYSES = PROJECT_DIR / "target" / "compiled" / "lumo_lending" / "analyses"
DEFAULT_DB = PROJECT_DIR / "lumo.duckdb"


def to_markdown(columns: list[str], rows: list[tuple]) -> str:
    """Minimal Markdown table renderer (no external dependency)."""
    cells = [[("" if v is None else str(v)) for v in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in cells:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(v))
    fmt = "| " + " | ".join(f"{{:<{w}}}" for w in widths) + " |"
    out = [fmt.format(*columns), "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    out += [fmt.format(*row) for row in cells]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pattern", default="*", help="glob over compiled analysis file names, e.g. 'dq_*'")
    ap.add_argument("--out", required=True, help="output Markdown file, relative to deliverables/")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="DuckDB file (default: lumo.duckdb)")
    ap.add_argument("--title", default=None, help="document title")
    args = ap.parse_args()

    if not COMPILED_ANALYSES.exists():
        print(f"No compiled analyses at {COMPILED_ANALYSES}. Run `dbt compile --select \"...\"` first.", file=sys.stderr)
        return 1

    files = sorted(p for p in COMPILED_ANALYSES.rglob("*.sql") if fnmatch.fnmatch(p.stem, args.pattern))
    if not files:
        print(f"No compiled analysis matches pattern {args.pattern!r}.", file=sys.stderr)
        return 1

    con = duckdb.connect(args.db, read_only=True)
    title = args.title or f"Analyses matching `{args.pattern}`"
    parts = [
        f"# {title}",
        "",
        f"Generated {dt.datetime.now():%Y-%m-%d %H:%M} by `scripts/run_analyses.py` "
        f"from the compiled SQL under `target/compiled/.../analyses/`. Warehouse: `{Path(args.db).name}` (read-only).",
        "",
    ]
    for f in files:
        sql = f.read_text(encoding="utf-8")
        try:
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            body = to_markdown(cols, rows)
            status = f"{len(rows)} row(s)"
        except Exception as exc:  # keep going, report the failure in the document
            body = f"```\nERROR: {exc}\n```"
            status = "ERROR"
        rel = f.relative_to(COMPILED_ANALYSES).as_posix()
        parts += [f"## {f.stem}", "", f"Source: `analyses/{rel}` — {status}", "", body, ""]
        print(f"{f.stem:<32} {status}")

    out_path = PROJECT_DIR / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"\nWrote {out_path.relative_to(PROJECT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
