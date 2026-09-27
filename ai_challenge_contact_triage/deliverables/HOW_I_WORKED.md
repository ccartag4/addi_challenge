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

### 3.5 A rule that read "hoy" as a payment date

- **What it produced:** the entity extractor treated any bare "ayer", "hoy" or "mañana" as a
  payment date. On the first six live classifications, the weather message MSG-037 ("qué
  opinan del clima hoy") came out with `payment_date = "hoy"`. The model had correctly left the
  field null; the rule added it, and the merge policy (rules win) kept it.
- **How I caught it:** by reading the outputs, not from a test. The verbatim verifier passed,
  because "hoy" is in the text; it checks that a value exists, not that it means what the field
  says.
- **What I did:** relative words now count only within a few words of a payment or due-date
  verb ("pagué ayer", "si pago hoy", "se vence mañana"); eleven sample messages pin the rule in
  both directions.
- **Lesson:** "code overrides the model" is only safe when the code is at least as precise as
  the model on that field. Verbatim verification is necessary, not sufficient; low-precision
  rules must either be tightened or defer to the model.

### 3.6 Three routing slips in one afternoon

- **What it produced:** the routing engine, written in one pass from the YAML policy, had three
  defects: the "no policy" override also swallowed the courtesy template for out-of-scope
  messages (order of evaluation), the out-of-scope template was still attached to sales
  inquiries that the policy says must go to a person, and `auto_reply` decisions carried the
  reason's default queue as if a case were open.
- **How I caught them:** the first two by the routing tests written from the policy's intent
  ("unrelated gets the template, sales gets a person"); the third by reading the first 18 live
  records, where an OTP question showed `auto_reply` with queue `soporte_tecnico`.
- **What I did:** the override now requires `reply_source: none`, a reason template applies
  only to auto actions without `no_draft`, and a queue is set only when a person is involved.
  Each fix has a test with the message it came from.
- **Lesson:** a policy engine is cheap to write and expensive to trust; the tests that pay are
  the ones phrased as the policy's sentences, not as the code's branches.

### 3.7 A verifier that rejected good Spanish

- **What it produced:** the first full run rejected 11 of 238 drafts. Reading them: five were
  rejected because the placeholder check (`TODO`, case-insensitive) matched the word "todo"
  ("queda todo actualizado"); two because the customer had written a number in words ("dos
  veces", "tercera vez") and the reply repeated it in words while the check only credited
  digits; and after I added ordinals, one more because "desde el primer día" became the figure 1.
- **How I caught it:** not by a test. The rejection list was short enough to read in full, and
  every rejected text was kept next to its failed check, which is why the pattern was obvious
  in minutes.
- **What I did:** word placeholders are now matched in upper case only; number words and
  ordinals are credited on the customer's side as well; "primer" is deliberately excluded. Each
  phrase became a test case; the run was replayed from cache at no cost and the rejections fell
  to four, all intended (three negated mentions of "condonación", one derived year).
- **Lesson:** a strict verifier is only credible if its false positives are counted and read.
  Keeping the rejected text in the record turned a debugging session into a five-minute review.

*(more cases added as they happen)*

## 4. What I would improve with more time

*(to be completed)*
