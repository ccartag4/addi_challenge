#!/usr/bin/env bash
# Single command for the AI challenge (macOS / Linux).
# Creates the virtual environment if missing, installs the pinned dependencies, runs the pipeline
# over ../data/messages.jsonl and writes output/triage_results.jsonl, output/batch_summary.json
# and output/batch_summary.md.
#
#   ./run.sh                        # auto: replays the committed cache, calls the API only for misses
#   ./run.sh --mode offline         # never calls the API (no key needed)
#   ./run.sh --limit 20             # any extra argument is passed to `python -m lumo_triage run`
#
# The API key is read from ANTHROPIC_API_KEY or from a local .env file (see .env.example).
set -euo pipefail
cd "$(dirname "$0")"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "Creating virtual environment in .venv ..."
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
    || { echo "Python 3.11 or newer is required (found: $(python3 --version))."; exit 1; }
  python3 -m venv .venv
fi

"$PY" -m pip install --quiet --disable-pip-version-check -r requirements.txt
exec "$PY" -m lumo_triage run --workers 4 "$@"
