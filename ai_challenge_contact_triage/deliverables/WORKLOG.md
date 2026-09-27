# Worklog — AI Challenge (contact triage)

Step-by-step trace of how the solution was built. One entry per step; each entry maps to a
commit. The plan these steps follow is in `IMPLEMENTATION_PLAN.md`. Same format as the data
challenge worklog.

---

## Step 00 — Analysis, profiling and plan  (2026-09-27)

**Goal:** understand the challenge and the data before writing code; record the decisions.

**Command(s):** profiling of `data/messages.jsonl` with a pandas/regex script (channels,
timestamp shapes, duplicates and near-duplicates, sensitive-data patterns, multi-intent, risk
signals, taxonomy gaps, rough keyword bucketing); Anthropic API reference loaded for model ids,
pricing, structured outputs and prompt caching; credential check on the machine (none present).

**Result:** findings in `IMPLEMENTATION_PLAN.md` §4 (regenerated as evidence in step 1).
Four decisions taken with the author (plan §3): personal key now and Addi's key when it arrives,
Claude Opus 5 with a measured Haiku 4.5 comparison, pytest + eval harness per Anthropic's guide,
human-confirmed gold set of 80–100 messages.

**Finding / decision:** an early observation of mojibake in one message was a console-rendering
artefact; the file has zero such characters. Corrected in the plan.

**Credential check (D1):** a personal key was placed in `deliverables/.env`; verified that the
file is git-ignored and untracked, that the value has the expected shape (never printed), and
that it authenticates: `models.retrieve("claude-opus-5")` OK and a 16-token
`messages.create` on `claude-opus-5` returned `end_turn` (19 input / 4 output tokens). The key
requested from Addi will replace it in the same file when it arrives.

**Environment:** Python 3.13 venv in `deliverables/.venv`; `anthropic 1.8.0`, `pydantic 2.13.5`,
`python-dotenv 1.2.3` installed during the check; the rest of the dependencies in step 0.

**Commit:** *(filled after commit)*
