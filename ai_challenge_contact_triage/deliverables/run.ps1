# Single command for the AI challenge (Windows PowerShell).
# Creates the virtual environment if missing, installs the pinned dependencies, runs the pipeline
# over ../data/messages.jsonl and writes output/triage_results.jsonl, output/batch_summary.json
# and output/batch_summary.md.
#
#   .\run.ps1                       # auto: replays the committed cache, calls the API only for misses
#   .\run.ps1 --mode offline        # never calls the API (no key needed)
#   .\run.ps1 --limit 20            # any extra argument is passed to `python -m lumo_triage run`
#
# The API key is read from ANTHROPIC_API_KEY or from a local .env file (see .env.example).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating virtual environment in .venv ..."
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
    if ($LASTEXITCODE -ne 0) { throw "Python 3.11 or newer is required (found: $(python --version))." }
    python -m venv .venv
}

& $py -m pip install --quiet --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

& $py -m lumo_triage run --workers 4 @args
exit $LASTEXITCODE
