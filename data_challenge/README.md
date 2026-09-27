# Data Challenge — Analytics Engineer

> Part of the **AI Solutions Technical Assessment**. Read the top-level
> `AI_amplifier_Technical_Assessment.md` first.

We would rather see a flawless, well-documented core than a broad scope half-finished. If
something falls outside what you can deliver, write it down in `ASSUMPTIONS.md` and explain how
you would have solved it.

**Using AI is allowed and expected.** We care about *how* you use it, not *whether* you use it.
Read the “AI log” section before you start: it is part of the deliverable and it is graded.

---

## 1. Business context

We are a point-of-sale lending fintech (BNPL). A customer applies for credit at a partner
merchant; if the application is approved and disbursed, it becomes a loan with a monthly
installment plan the customer pays down over time. We operate in Colombia (COP); **leadership
reports everything in USD**.

The data you receive are raw extracts from three different systems, none of which was designed for
analytics: the origination core (CDC), a payment processor that was migrated mid-2025, and an
append-only merchant master.

Today the Risk team and the Merchant team ask for the same numbers and get different answers. Your
job is to build the layer that settles the argument.

## 2. Stack

- **dbt + Databricks / Snowflake / … any other data lake.** Load the CSVs in `data/` as raw
tables.
- Medallion architecture: **Bronze → Silver → Gold**. Use whatever dbt layer convention you
prefer (`staging` / `intermediate` / `marts` is perfectly valid) as long as the separation of
responsibilities is explicit.

## 3. Input data (`data/`)

| File | Rows | What it is |
| --- | --- | --- |
| `raw_applications_cdc.csv` | ~128k | Credit applications, in CDC format (multiple rows per application) |
| `raw_loans.csv` | ~28k | Disbursed loans |
| `raw_installments.csv` | ~130k | Installment plan for each loan |
| `raw_payments.csv` | ~112k | Payments received (two source systems) |
| `raw_customers.csv` | 30k | Customer master |
| `raw_merchants_history.csv` | ~860 | Merchant attribute history (append-only) |
| `raw_fx_rates.csv` | ~850 | Published FX rates |

Column-level detail and semantics are in **`data/data_dictionary.md`**. Read it: it contains business
rules that are not evident from the data alone.

## 4. What to build

### 4.1 Core (required)

**Silver** — clean, deduplicated entities with a declared grain:

1. `dim_customer` — one record per **real person**, not per `customer_id`.
2. `dim_merchant` — **SCD type 2**, derived from the append-only history (with `valid_from`,
`valid_to`, `is_current`).
3. `fct_application` — one row per application, in its final state.
4. `fct_loan` — one row per valid loan, with amounts in USD as well.
5. `fct_payment` — one row per **effective** payment (net of reversals), normalized across source
systems.
6. `fct_installment_status` — grain `loan_id × installment_number`, with how much of each
installment was paid, when it was settled, and how many days past due it accrued.

**Gold** — consumption models:

1. `agg_merchant_monthly` — grain `merchant × month`: applications, approval rate, GMV in USD,
disbursed loans, FPD30 and PAR30. The merchant must be reported under the category it held **on
the date of the event**, not its current one.
2. `dm_loan_delinquency_snapshot` — snapshot as of **2026-06-30**: per loan, outstanding balance
in USD, DPD (days past due) and delinquency bucket (`0`, `1-30`, `31-60`, `61-90`, `90+`).

### 4.2 Definitions you must consider

- **Business day**: operations close in `America/Bogota`. Every business date derives from UTC
timestamps converted to that timezone.
- **GMV**: principal disbursed, converted to USD **at the rate of the disbursement date**.
- **Approval rate**: approved applications / valid applications in the period.
- **FPD30** (First Payment Default): share of loans whose **first installment** went more than 30
days past due — that is, it was paid more than 30 days after its due date, or it is still unpaid
and more than 30 days have elapsed. Only loans whose first installment has already reached the
30-day mark as of the cutoff date belong in the denominator.
- **PAR30** (Portfolio at Risk): outstanding balance in USD of loans with DPD > 30, divided by
total outstanding balance. A loan’s outstanding balance is the sum of its **unsettled**
installments (both overdue and not yet due).
- **Loan DPD**: days elapsed since the due date of its oldest unpaid installment.
- **Payment allocation**: payments arrive at the loan level, not the installment level. Apply them
**FIFO** (the oldest payment settles the oldest outstanding installment); one payment may settle
several installments, and one installment may require several payments.

### 4.3 Business questions (answer with figures)

In `RESULTS.md`, giving the number and the model or query that produces it:

1. How many valid applications and how many approved, in total? Global approval rate.
2. How many valid loans were disbursed, and what is total GMV in USD?
3. GMV in USD and loan count for the **2026-01** disbursement cohort.
4. Global FPD30, and FPD30 for the **2026-01** cohort.
5. PAR30 as of **2026-06-30**, and total outstanding balance in USD at that date.
6. Top 5 merchants by GMV in USD. What does that distribution tell you about the business, and
about the concentration risk in your own metrics?
7. How many real people are in the customer master, and how many `customer_id`s are redundant?

### 4.4 Quality and contract

- dbt tests where they matter: uniqueness and non-nullity of grain keys, referential integrity,
ranges and accepted values, and **at least two business tests of your own** (singular tests or
`dbt_utils`) that catch something you discovered in the data.
- Documentation (`schema.yml`) for the Gold models and for any column whose calculation isn’t
straightforward.
- Declare the grain of every model in its description.

### 4.5 Nice to have

- Incremental materialization for the highest-volume models, with a justified strategy.
- Late-arriving data handling.
- `dbt_constraints`/contracts, exposures, or a snapshot model for the SCD2 dimension.

## 5. Deliverable

Put your work in `deliverables/` (per the top-level instructions):

```
deliverables/
  dbt_project.yml
  models/            # the dbt models
  tests/
  RESULTS.md         # answers to 4.3
  ASSUMPTIONS.md     # numbered assumptions + data quality findings
  AI_LOG.md
  README.md          # how to run it in 3 commands
```

## 6. AI log (`AI_LOG.md`) — required

We want to see your judgment steering the tool, not the tool steering you. Deliver a file with:

1. **What you delegated and what you didn’t**, and why.
2. **3–5 key prompts** you consider most decisive to your solution — the ones that changed the
direction of the work, not the trivial ones.
3. **At least two cases where the AI got it wrong**: what it produced, how you caught it, and what
you did about it. If you found none, tell us how you verified there were none.
4. **How you verified the final numbers** in `RESULTS.md`.

There is no penalty for heavy AI use. There is a penalty for shipping code you can’t explain or
numbers you can’t defend.