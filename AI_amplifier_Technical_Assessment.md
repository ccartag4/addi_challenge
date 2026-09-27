# AI Solutions — Technical Assessment

---

## General Instructions

Welcome, and thank you for taking the time to do this.

You will find **two challenges** in this repository: an **AI challenge** and a **data challenge**. Both come from real internal use cases; the data is fully synthetic.


### Timeline

You have **5 calendar days**. Budget roughly **6–8 hours** of actual work across both challenges. If you need more time, let us know in advance.

### AI tools — expected

We **expect you to use AI tools** throughout. What we care about is *how*: how you prompt, how you validate what they produce, and where you catch them being wrong.

For each challenge, include a short note on how you used the provided tools.

The one hard requirement: **you must be able to explain and defend every part of what you submit.**

### Submission

- Work inside the two challenge folders.
- Push your work to a GitHub repository and share the link with us.
- Include the write-ups described under **Deliverables**.

### Environment & how to run

- **The AI challenge solution** must be reproducible on our end — we run it after you submit. Include a single command that sets it up and runs it over the data we provided, writing its output to a file (submit that output too).
- **The data challenge solution** depends on the warehouse you choose (Databricks, Snowflake, a local dbt setup, etc.), so we may not be able to execute your pipeline ourselves. Include a short, reproducible set of commands regardless, and make sure `RESULTS.md` plus your own run's output let us verify your numbers without needing to re-run it (see `data_challenge/README.md` for the exact deliverable).

If you need an LLM provider API key, tell us and we'll give you one.

### Follow-up

After you submit, we will have a conversation where you walk us through both solutions and the decisions behind them.

### Questions?

If anything is unclear about the setup, reach out. We would rather answer a question than have you build on a wrong assumption.

---


## The two challenges

Both are set at **Lumo**, a fictional consumer-credit (buy-now-pay-later) company. You have just joined to help internal teams build AI-powered and data-driven solutions.

| | AI Challenge | Data Challenge |
|---|---|---|
| **Team** | Customer Experience (CX) | Analytics Engineering |
| **Folder** | `ai_challenge_contact_triage/` | `data_challenge/` |
| **In one line** | Triage and draft replies for incoming customer messages | Build a dbt Bronze→Silver→Gold model over Lumo's lending data and answer key portfolio questions |

Read both before you start.

---

### AI Challenge — Contact triage & reply drafting (CX team)

**Folder:** `ai_challenge_contact_triage/`

Lumo's CX team gets a constant stream of customer messages across chat, email and WhatsApp — installments, payment dates, people who can't pay this month, app and login issues, data updates, complaints, and noise. Today an agent reads each one, decides what it's about, sets a priority, and either answers it or routes it. It doesn't scale, and the repetitive ones eat the team's time.

They need a component that takes an incoming message and produces a structured, reliable output the ticketing system can act on: what it's about, how urgent it is, the key details from the text, whether it can be auto-answered or needs a human, and — when it can be answered — a grounded draft reply based on Lumo's policies.

The sample data is synthetic and only a few hundred messages, but in production this is a high-volume stream (~10,000 messages/day).

See `ai_challenge_contact_triage/README.md` for details and deliverables.

---

### Data Challenge — Lending data warehouse (Analytics Engineering)

**Folder:** `data_challenge/`

You'll receive raw extracts from three systems of a point-of-sale lending fintech: a CDC log of credit applications, a payment processor migrated mid-2025, and an append-only merchant master. Using dbt over the warehouse of your choice, build a Bronze → Silver → Gold model that turns them into trustworthy dimensions, facts, and two consumption models — merchant performance by month and a loan delinquency snapshot. Then answer seven business questions with figures you can extract from the final gold datasets.

See `data_challenge/README.md` for details and deliverables.

---


## Deliverables

For **each** challenge:

1. **A working solution**, inside that challenge's `deliverables/` folder.
2. **An AI usage write-up**, also inside `deliverables/`: how you used the provided tools, how you validated their output, and where you had to correct them. The exact file name and format is specified in each challenge's own README — `HOW_I_WORKED.md` for the AI challenge, `AI_LOG.md` for the data challenge.

## A few things that help

- These are customer records — handle the data carefully.
- Be ready to walk us through every decision.

Good luck — we're looking forward to seeing how you think.
