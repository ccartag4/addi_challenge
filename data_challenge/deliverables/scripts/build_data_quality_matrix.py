"""
Generate DATA_QUALITY.md: the DAMA-DMBOK data quality matrix of this dbt project.

Reads two dbt artifacts:
  target/manifest.json     every test, its config.meta.dq_dimension, severity and the model it
                           is attached to
  target/run_results.json  the status (pass / warn / fail / error) and failure count of each
                           test in the last `dbt build` / `dbt test`

Usage (from deliverables/, after `dbt build`):

    python scripts/build_data_quality_matrix.py            # writes DATA_QUALITY.md
    python scripts/build_data_quality_matrix.py --out evidence/data_quality_run.md

Nothing here is typed by hand: if a test is added, removed or changes dimension, rerunning
this script updates the matrix.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_DIR / "target" / "manifest.json"
RUN_RESULTS = PROJECT_DIR / "target" / "run_results.json"

DIMENSIONS = ["completeness", "uniqueness", "validity", "accuracy", "consistency", "integrity", "timeliness"]
DIMENSION_MEANING = {
    "completeness": "required values are present (not_null, coverage of a calendar or a population)",
    "uniqueness": "one record per real-world entity at the declared grain",
    "validity": "values conform to type, format, domain and range",
    "accuracy": "values reflect the real fact (scale, conversion, conservation of money)",
    "consistency": "the same fact agrees across models and across definitions",
    "integrity": "relationships resolve (referential integrity, point-in-time coverage)",
    "timeliness": "ordering and dating are correct (event vs ingest time, cutovers, as-of dates)",
}
LAYER_ORDER = ["bronze", "silver/staging", "silver/intermediate", "silver/core", "gold", "seed", "other"]
STATUS_MARK = {"pass": "✅", "warn": "⚠️", "fail": "❌", "error": "💥", "skipped": "⏭️", "not run": "·"}


def layer_of(node: dict) -> str:
    path = node.get("original_file_path", "").replace("\\", "/")
    if node.get("resource_type") == "seed":
        return "seed"
    for candidate in ("silver/staging", "silver/intermediate", "silver/core", "bronze", "gold"):
        if f"/{candidate}/" in f"/{path}":
            return candidate
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="DATA_QUALITY.md", help="output file, relative to deliverables/")
    args = ap.parse_args()

    if not MANIFEST.exists() or not RUN_RESULTS.exists():
        print("Run `dbt build` first: target/manifest.json and target/run_results.json are required.", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    run_results = json.loads(RUN_RESULTS.read_text(encoding="utf-8"))
    nodes = manifest["nodes"]
    results = {r["unique_id"]: r for r in run_results["results"]}
    generated_at = run_results["metadata"]["generated_at"]

    # ---- collect tests ---------------------------------------------------------------------
    tests = []
    for uid, node in nodes.items():
        if node.get("resource_type") != "test":
            continue
        meta = (node.get("config") or {}).get("meta") or node.get("meta") or {}
        dimension = meta.get("dq_dimension", "unclassified")
        attached = node.get("attached_node")
        if attached is None:  # singular test: every model it refs
            attached_ids = [d for d in node.get("depends_on", {}).get("nodes", []) if d.split(".")[0] in ("model", "seed")]
        else:
            attached_ids = [attached]
        kind = "generic: " + node["test_metadata"]["name"] if node.get("test_metadata") else "singular"
        res = results.get(uid)
        status = res["status"] if res else "not run"
        failures = res.get("failures") if res else None
        tests.append({
            "uid": uid,
            "name": node["name"],
            "dimension": dimension,
            "severity": str((node.get("config") or {}).get("severity", "error")).lower(),
            "kind": kind,
            "status": status,
            "failures": failures,
            "models": [nodes[m]["name"] if m in nodes else m for m in attached_ids],
            "layer": layer_of(nodes[attached_ids[0]]) if attached_ids and attached_ids[0] in nodes else "other",
        })

    models = {uid: n for uid, n in nodes.items() if n.get("resource_type") in ("model", "seed")}
    dims_present = [d for d in DIMENSIONS if any(t["dimension"] == d for t in tests)]
    extra_dims = sorted({t["dimension"] for t in tests} - set(DIMENSIONS))
    dims_present += extra_dims

    # ---- section 1: totals per dimension ---------------------------------------------------
    lines = [
        "# Data Quality — DAMA-DMBOK matrix",
        "",
        f"Generated {dt.datetime.now():%Y-%m-%d %H:%M} by `scripts/build_data_quality_matrix.py` from "
        f"`target/manifest.json` and `target/run_results.json` (run of {generated_at[:19]}Z). "
        f"{len(tests)} tests over {len(models)} models and seeds.",
        "",
        "Every dbt test in this project declares the DMBOK dimension it protects "
        "(`config.meta.dq_dimension`). Findings and assumptions behind each test are in "
        "`ASSUMPTIONS.md`; the step that introduced it is in `WORKLOG.md` and `DATA_JOURNEY.md`.",
        "",
        "## 1. Dimensions",
        "",
        "| Dimension | Meaning in this project | Tests | Pass | Warn | Fail |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for d in dims_present:
        sub = [t for t in tests if t["dimension"] == d]
        c = Counter(t["status"] for t in sub)
        lines.append(f"| **{d}** | {DIMENSION_MEANING.get(d, '')} | {len(sub)} | {c.get('pass', 0)} | {c.get('warn', 0)} | {c.get('fail', 0) + c.get('error', 0)} |")
    c_all = Counter(t["status"] for t in tests)
    lines.append(f"| **total** | | {len(tests)} | {c_all.get('pass', 0)} | {c_all.get('warn', 0)} | {c_all.get('fail', 0) + c_all.get('error', 0)} |")

    # ---- section 2: matrix model x dimension -----------------------------------------------
    lines += ["", "## 2. Matrix: model × dimension (number of tests; ⚠️ = warns, ❌ = fails)", ""]
    header = "| Layer | Model | " + " | ".join(dims_present) + " | Total |"
    lines += [header, "|---|---|" + "---:|" * (len(dims_present) + 1)]
    per_model = defaultdict(lambda: defaultdict(list))
    for t in tests:
        for m in t["models"]:
            per_model[m][t["dimension"]].append(t)
    model_rows = []
    for uid, n in models.items():
        model_rows.append((LAYER_ORDER.index(layer_of(n)) if layer_of(n) in LAYER_ORDER else 99, layer_of(n), n["name"]))
    for _, layer, name in sorted(model_rows):
        cells = []
        total = 0
        for d in dims_present:
            ts = per_model[name].get(d, [])
            total += len(ts)
            if not ts:
                cells.append("")
                continue
            marks = "".join(STATUS_MARK[s] for s in ("warn", "fail", "error") for t in ts if t["status"] == s)
            cells.append(f"{len(ts)}{marks}")
        lines.append(f"| {layer} | `{name}` | " + " | ".join(cells) + f" | {total} |")

    # ---- section 3: singular (business) tests ----------------------------------------------
    lines += ["", "## 3. Business tests (singular)", "", "| Test | Dimension | Models | Status |", "|---|---|---|---|"]
    for t in sorted((t for t in tests if t["kind"] == "singular"), key=lambda t: t["name"]):
        st = f"{STATUS_MARK.get(t['status'], t['status'])} {t['status']}" + (f" ({t['failures']} rows)" if t["failures"] else "")
        lines.append(f"| `{t['name']}` | {t['dimension']} | {', '.join(f'`{m}`' for m in t['models'])} | {st} |")

    # ---- section 4: non-passing tests ------------------------------------------------------
    lines += ["", "## 4. Tests not passing in the last run", ""]
    bad = [t for t in tests if t["status"] != "pass"]
    if not bad:
        lines.append("None.")
    else:
        lines += ["| Test | Dimension | Severity | Status | Failing rows | Models |", "|---|---|---|---|---:|---|"]
        for t in sorted(bad, key=lambda t: (t["status"], t["name"])):
            lines.append(f"| `{t['name']}` | {t['dimension']} | {t['severity']} | {t['status']} | {t['failures'] if t['failures'] is not None else ''} | {', '.join(f'`{m}`' for m in t['models'])} |")

    # ---- section 5: coverage ---------------------------------------------------------------
    untested = [n["name"] for n in models.values() if not per_model.get(n["name"])]
    lines += ["", "## 5. Coverage", "", f"Models and seeds with at least one test: {len(models) - len(untested)} of {len(models)}."]
    if untested:
        lines.append("Without tests: " + ", ".join(f"`{m}`" for m in sorted(untested)) + ".")
    unclassified = [t["name"] for t in tests if t["dimension"] == "unclassified"]
    lines.append(f"Tests without a DMBOK dimension: {len(unclassified)}." + (" " + ", ".join(f"`{n}`" for n in unclassified) if unclassified else ""))

    # ---- section 6: full detail -----------------------------------------------------------
    lines += ["", "## 6. All tests", "", "| Layer | Model(s) | Test | Kind | Dimension | Severity | Status |", "|---|---|---|---|---|---|---|"]
    for t in sorted(tests, key=lambda t: (LAYER_ORDER.index(t["layer"]) if t["layer"] in LAYER_ORDER else 99, t["models"][0] if t["models"] else "", t["name"])):
        lines.append(f"| {t['layer']} | {', '.join(f'`{m}`' for m in t['models'])} | `{t['name']}` | {t['kind']} | {t['dimension']} | {t['severity']} | {STATUS_MARK.get(t['status'], '')} {t['status']} |")

    out = PROJECT_DIR / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"tests: {len(tests)}  pass: {c_all.get('pass', 0)}  warn: {c_all.get('warn', 0)}  fail: {c_all.get('fail', 0) + c_all.get('error', 0)}")
    print(f"Wrote {out.relative_to(PROJECT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
