# Architecture — how the warehouse is built and how the numbers flow

Diagrams are Mermaid; GitHub renders them inline. In VS Code, use the "Markdown Preview Mermaid
Support" extension or read the text form under each diagram.

## 1. Lineage: from the seven CSV extracts to the two gold models

```mermaid
flowchart LR
    subgraph RAW["Raw extracts (../data, CSV)"]
        r_app["raw_applications_cdc"]
        r_loan["raw_loans"]
        r_inst["raw_installments"]
        r_pay["raw_payments"]
        r_cust["raw_customers"]
        r_mer["raw_merchants_history"]
        r_fx["raw_fx_rates"]
    end
    subgraph BRZ["Bronze: 7 views, every column as text"]
        b_app["brz_applications_cdc"]
        b_loan["brz_loans"]
        b_inst["brz_installments"]
        b_pay["brz_payments"]
        b_cust["brz_customers"]
        b_mer["brz_merchants_history"]
        b_fx["brz_fx_rates"]
    end
    subgraph STG["Silver / staging: typed, parsed, deduplicated"]
        s_app["stg_applications_cdc"]
        s_loan["stg_loans"]
        s_inst["stg_installments"]
        s_pay["stg_payments"]
        s_cust["stg_customers"]
        s_mer["stg_merchants_history"]
        s_fx["stg_fx_rates"]
    end
    subgraph INT["Silver / intermediate: business rules"]
        i_ev["int_application_events<br/>CDC ranks (A2)"]
        i_fx["int_fx_daily<br/>forward fill (A7)"]
        i_lv["int_loan_validated<br/>verdict + reason (A5)"]
        i_pc["int_payment_classified<br/>reversals (A9)"]
        i_pa["int_payment_allocation<br/>FIFO (A21)"]
        i_me["int_loan_month_end_status<br/>stock per month end (A13)"]
    end
    subgraph CORE["Silver / core: dimensions and facts"]
        c_app["fct_application"]
        c_mer["dim_merchant (SCD2)"]
        c_cust["dim_customer (person grain)"]
        c_br["bridge_customer_person"]
        c_loan["fct_loan (USD)"]
        c_pay["fct_payment (effective)"]
        c_is["fct_installment_status (as-of)"]
    end
    subgraph GOLD["Gold: consumption"]
        g_dm["dm_loan_delinquency_snapshot"]
        g_agg["agg_merchant_monthly"]
    end
    subgraph EXP["Exposures"]
        e_risk(["Risk: delinquency review"])
        e_mer(["Merchant team: performance report"])
    end
    seed[("seed: city_canonical")]

    r_app --> b_app --> s_app --> i_ev --> c_app
    r_loan --> b_loan --> s_loan --> i_lv --> c_loan
    r_inst --> b_inst --> s_inst --> c_loan
    s_inst --> i_pa
    s_inst --> c_is
    r_pay --> b_pay --> s_pay --> i_pc --> c_pay --> i_pa --> c_is
    r_cust --> b_cust --> s_cust --> c_cust --> c_br
    seed --> c_cust
    r_mer --> b_mer --> s_mer --> c_mer
    r_fx --> b_fx --> s_fx --> i_fx --> c_loan
    i_fx --> c_pay
    c_app --> i_lv
    c_mer --> c_loan
    c_br --> c_loan
    c_loan --> c_pay
    c_loan --> c_is
    c_is --> g_dm
    c_is --> i_me --> g_agg
    c_loan --> g_dm
    c_app --> g_agg
    g_dm --> g_agg
    c_mer --> g_agg
    g_dm --> e_risk
    g_agg --> e_risk
    g_agg --> e_mer
```

Text form: each CSV is read 1:1 into a bronze view; staging types and deduplicates it;
intermediate models apply one business rule each (CDC final state, FX calendar, loan validity,
reversal classification, FIFO allocation, month-end series); core models are the six entities
the README asks for; the two gold models aggregate and classify; two exposures name the
consumers. Layer responsibilities:

| Layer | Schema | Materialization | Responsibility | Must not do |
|---|---|---|---|---|
| Bronze | `bronze` | view | show the extract exactly as delivered | cast, filter, deduplicate |
| Staging | `silver` | view | types, timestamp parsing (3 shapes), Bogotá dates, exact dedup, sentinels | apply business rules |
| Intermediate | `silver` | table | one business rule per model, keeping every row with a flag or a reason | drop rows silently |
| Core | `silver` | table | the entities at their declared grain, filtered by the rules | recompute upstream logic |
| Gold | `gold` | table | aggregate and classify for consumers | re-implement FIFO or as-of logic |
| dq_audit | `dq_audit` | tables | rows that failed each test (`store_failures`) | |

## 2. How the risk metrics are produced (Q4, Q5 and the monthly PAR30)

```mermaid
flowchart TD
    P["fct_payment<br/>effective payments, running total per loan"] --> F["int_payment_allocation<br/>FIFO by interval overlap: one row per payment x installment"]
    I["stg_installments<br/>plan: loan x installment, due_date, amount_due"] --> F
    F --> S["fct_installment_status<br/>as of snapshot_date: paid_amount, settled_date,<br/>days_past_due, is_fpd30_eligible, is_fpd30"]
    FX["int_fx_daily<br/>rate for every calendar day"] --> D
    FX --> M
    S --> D["dm_loan_delinquency_snapshot<br/>per loan: outstanding (A11), DPD (A24), bucket, is_par30, USD (A12)"]
    S --> M["int_loan_month_end_status<br/>per loan x month end, from settled_date_any"]
    D --> Q4["Q4: FPD30 = flagged / eligible first installments"]
    D --> Q5["Q5: PAR30 = outstanding USD of DPD > 30 / total outstanding USD"]
    M --> A["agg_merchant_monthly<br/>par30_rate = stock at month end (A13)"]
    D --> A
    A -. "at 2026-06-30 both agree loan by loan<br/>(assert_month_end_series_matches_snapshot)" .- D
```

### FIFO by interval overlap (no recursion)

Per loan, installments form consecutive segments on a *debt line* and payments form consecutive
segments on a *money line*; a payment funds an installment by the length of the overlap.

```
debt line   |---- inst 1: 428,600 ----|---- inst 2: 428,600 ----|---- inst 3: 428,600 ----|
            0                     428,600                   857,200                 1,285,800
money line  |------------ payment A: 857,200 ---------------|--- payment B: 428,600 ---|
            0                                           857,200                 1,285,800

allocation: A -> inst 1: 428,600   A -> inst 2: 428,600   B -> inst 3: 428,600
settled_date(inst 1) = settled_date(inst 2) = date of A ;  settled_date(inst 3) = date of B
```

Real example from the data (`int_payment_allocation`, loan with the split payment 4000023):
one payment of 857,200 covers installments 1 and 2; installment 4 (428,500) is completed by two
payments of 257,100 and 171,400. Four singular tests guarantee conservation: no payment funds
more than its amount, no installment receives more than its due, money never reaches a later
installment while an earlier one is unsettled, and per loan allocated = received capped at the
plan total.

## 3. The working method (one loop per step, 00 to 19)

```mermaid
flowchart LR
    plan["IMPLEMENTATION_PLAN<br/>step N"] --> draft["AI assistant drafts<br/>SQL / YAML / tests / analysis"]
    draft --> scratch["AI validates in a scratch copy<br/>dbt clean, deps, build from zero"]
    scratch -- "fails" --> draft
    scratch -- "passes" --> review["David reads every file<br/>line by line"]
    review --> run["David runs the commands<br/>dbt build, analyses, scripts"]
    run --> paste["Output pasted back"]
    paste -- "unexpected" --> draft
    paste -- "as expected" --> record["WORKLOG, DATA_JOURNEY,<br/>ASSUMPTIONS, AI_LOG updated"]
    record --> commit["one commit per step, pushed"]
    commit --> plan
```

Every arrow back to *draft* is an entry in `DATA_JOURNEY.md` section C (error ledger) and, when
the assistant was the cause, in `AI_LOG.md` section 3.

## 4. How the published figures were verified

```mermaid
flowchart TD
    L1["1. Day-one pandas anchors,<br/>written before any model existed"] --> L2["2. Row-count funnel (dq_15):<br/>every delta between layers has a finding or assumption number"]
    L2 --> L3["3. 244 dbt tests, 16 of them business tests:<br/>reconciliations across layers on every build"]
    L3 --> L4["4. Open definitions published with their alternative<br/>(A11, A12, A13, Q3 UTC, Q7 document+country)"]
    L4 --> L5["5. Independent pandas recomputation from the raw CSVs:<br/>own parser, own CDC resolution, FIFO as a loop in cents<br/>24 of 24 checks, DPD and balance equal on all 27,955 loans"]
    L5 --> R["RESULTS.md"]
```

## 5. Where each README requirement is met

| README 4.x requirement | Where |
|---|---|
| 4.1 Silver: `dim_customer` (real person), `dim_merchant` (SCD2), `fct_application`, `fct_loan` (USD), `fct_payment` (effective), `fct_installment_status` (grain loan × installment) | `models/silver/core/` |
| 4.1 Gold: `agg_merchant_monthly` with category as of the event date; `dm_loan_delinquency_snapshot` as of 2026-06-30 | `models/gold/` |
| 4.2 Business day in Bogotá | macros `to_business_date`, A6 |
| 4.2 GMV at disbursement-date rate | `fct_loan.principal_usd`, `int_fx_daily`, A7 |
| 4.2 Approval rate, FPD30, PAR30, loan DPD | `fct_application`, `fct_installment_status`, `dm_loan_delinquency_snapshot`, A23, A24 |
| 4.2 FIFO payment allocation | `int_payment_allocation`, A21, four conservation tests |
| 4.3 Seven questions with figures and the producing model or query | `RESULTS.md`, `analyses/results/`, `evidence/results.md` |
| 4.4 Tests: grain keys, referential integrity, ranges, accepted values, at least two business tests | 244 tests, 16 singular, `DATA_QUALITY.md` |
| 4.4 Documentation of gold models and non-trivial columns; grain in every description | `models/*/*.yml`, `dbt docs generate` |
| 4.5 Nice to have | exposures done; incremental, late arrivals, snapshot, contracts described in `ASSUMPTIONS.md` §C |
| 5 Deliverables layout | this folder |
| 6 AI log | `AI_LOG.md` (4 sections, 7 error cases) |
| Top-level: reproducible commands, verifiable without re-running | `README.md`, `evidence/` (queries, cross-check, dbt artefacts, build log) |
