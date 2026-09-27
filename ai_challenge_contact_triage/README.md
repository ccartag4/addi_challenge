# AI Challenge — Contact triage & reply drafting

> Part of the **AI Solutions Technical Assessment**. Read the top-level
> `AI_amplifier_Technical_Assessment.md` first.

## The situation

Lumo (a fictional consumer-credit / buy-now-pay-later company) has a CX team that receives a
constant stream of customer messages across chat, email and WhatsApp: questions about
installments and payment dates, people who can't pay this month, app and login issues, data
updates, complaints, requests to be removed from the credit bureaus, and a fair amount of noise.

Right now a human reads every message, decides what it's about, sets a priority, and either
answers it or routes it to the right queue. The easy, repetitive ones are most of the volume and
eat the team's time.

> **On scale:** the sample in `data/messages.jsonl` is synthetic and only a few hundred messages.
> In production this is a **high-volume** stream — on the order of **~10,000 messages per day**.
> Keep that in mind in how you approach the problem.

## What they need

A component that takes **one incoming message** and returns a **structured, reliable result** the
ticketing system can act on. At minimum, for each message:

- **What it's about** — a contact reason from the taxonomy (see `taxonomy.md`; refine it if you find it lacking).
- **Priority / urgency** — your call on how to model this.
- **Key details extracted from the text** — whatever is useful and present (e.g. a credit/ID number, an amount, a payment date, a channel-specific identifier). Don't invent data that isn't there.
- **What to do with it** — can it be safely auto-answered, or does it need a human? If it needs a human, which queue?
- **A draft reply** — *only when it can be answered*, grounded in Lumo's policies (`knowledge_base/`). If the policy doesn't cover it, that itself is a signal.

On top of the per-message result, produce a **short summary of the whole batch** (e.g. volume by
reason, how much looks auto-answerable, anything that stands out).

Some messages are messy: multi-intent, out of scope, ambiguous, or just noise. Handling those
sensibly is part of the problem.

## What's in this folder

| Path | What it is |
|------|------------|
| `data/messages.jsonl` | The batch of incoming customer messages (one JSON object per line). Synthetic. |
| `taxonomy.md` | A starting taxonomy of contact reasons. You may extend or change it. |
| `knowledge_base/` | Lumo's policy snippets, to ground replies. Intentionally incomplete in places. |
| `deliverables/` | Where your work goes. |

## Deliverables

In `deliverables/` (and per the top-level instructions):

1. **A working solution** that processes `data/messages.jsonl` and writes a structured result per
   message plus the batch summary to an output file.
2. **The output file** from your own run.
3. **`HOW_I_WORKED.md`** — how you used the provided tools, how you validated the
   output, and what you'd improve with more time.

## Notes

- The messages are in Spanish (Colombian customers). Your output structure can be in whatever
  language you prefer; replies should be in Spanish.
- Don't hard-code answers to the specific sample messages — the component should generalize to new ones.
