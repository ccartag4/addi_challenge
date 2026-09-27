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

*(more cases added as they happen)*

## 4. What I would improve with more time

*(to be completed)*
