# HOW I WORKED — AI Challenge

> Required deliverable. Filled in as the work happens. Tool used: Claude Code (Anthropic) inside
> VS Code, with the Anthropic Python SDK for the pipeline itself.

## 1. How I used the tools

*(to be completed: what was delegated to the assistant, what I kept, how prompts were written and
versioned, how the model was chosen)*

## 2. How I validated the output

*(to be completed: schema validation, deterministic verifier, pytest, human-confirmed gold set,
LLM-judge calibration, offline determinism, adversarial fixtures)*

## 3. Where the AI was wrong

### 3.1 A "mojibake" that was not there

- **What it produced:** on the first read of the messages the assistant reported one message with
  broken encoding (`aÃ±o`).
- **How I caught it:** the profiling script counted zero occurrences of the character in the file;
  the artefact came from PowerShell rendering UTF-8 on the console.
- **What I did:** removed the "encoding fix" from the plan; kept unicode NFC normalisation only.

### 3.2 Ambiguous YAML, for the second time in this assessment

- **What it produced:** `taxonomy.yaml` with three values YAML cannot parse as intended: a note
  containing `: `, a description starting with a double quote, and priority descriptions with
  commas inside `{...}` flow mappings, which YAML reads as extra keys.
- **How I caught it:** the consistency test suite failed at collection with a `ScannerError` at
  a line and column; the same mistake had already happened in the data challenge (`gold.yml`).
- **What I did:** quoted the three values and kept the tests loading both policy files, so a
  malformed policy fails the build before any message is processed.
- **Lesson:** free text inside YAML must be quoted by default; an assistant that writes prose
  into config files will trip on this again unless a test parses the file.

### 3.3 A library function that does not exist

- **What it produced:** near-duplicate detection built on `rapidfuzz.distance.Jaccard` with
  `process.cdist`, presented as the scale-aware choice for a 10,000-message day.
- **How I caught it:** the very first import in the test run failed: `cannot import name
  'Jaccard' from 'rapidfuzz.distance'`. The installed 3.14.6 ships Levenshtein, Jaro, Indel and
  friends, not Jaccard; the assistant wrote the call from memory of an older API.
- **What I did:** kept the definition that the evidence already used (token Jaccard ≥ 0.6) in
  plain Python with union-find, noted MinHash/LSH as the path beyond tens of thousands of
  messages, and removed the now-unused dependency from `requirements.txt` and the lock.
- **Lesson:** the same failure class as the dbt deprecations in the data challenge: library
  surfaces drift and the assistant's memory lags them. An import test on day one costs nothing.

### 3.4 Evidence and code that disagreed by one duplicate

- **What it produced:** the profiling script reported 3 exact duplicates; the pipeline code found
  4, then 2, depending on how punctuation-only messages were treated.
- **How I caught it:** a test pins the code's duplicate count to the evidence file; it failed
  twice, each time for a different reason: first because `...` and `?????` hashed to the same
  empty content, then because the profiling normaliser left double spaces where commas had been
  and missed the pair MSG-155 / MSG-207.
- **What I did:** excluded content-free messages from deduplication in both places, gave the
  profiling script the exact same canonical form as the code, regenerated the evidence and
  corrected the figure in the plan. The test now names the two pairs instead of a count.
- **Lesson:** a number in an evidence file is only trustworthy if the code that produces the
  pipeline is tested against it; the disagreement was small, the habit it enforces is not.

*(more cases added as they happen)*

## 4. What I would improve with more time

*(to be completed)*
