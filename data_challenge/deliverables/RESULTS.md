# RESULTS — Lumo lending warehouse

Answers to the seven business questions of `data_challenge/README.md` §4.3, as of the
snapshot date **2026-06-30**, produced by the dbt project in this folder on DuckDB.

**How to verify without re-running.** Every figure below is produced by a committed query under
`analyses/results/` and its output is committed in `evidence/results.md`. The same figures were
recomputed independently from the raw CSVs by `scripts/crosscheck_pandas.py`
(`evidence/crosscheck_pandas.md`: 24 of 24 checks match, including DPD and balance on every
loan). The test run behind them is in `evidence/dbt_artifacts/run_results.json` and
`evidence/dbt_build.log` (273 pass, 1 expected warn, 0 fail). To re-run: see `README.md`.

**Definitions** are numbered A1–A25 in `ASSUMPTIONS.md`; data quality findings F1–F18 in the
same file; the row-by-row accounting of every transformation in `DATA_JOURNEY.md`.

## Summary

| # | Question | Answer | Produced by |
|---|---|---|---|
| 1 | Valid applications, approved, approval rate | **59,059** valid · **33,007** approved · **55.8882 %** | `silver.fct_application` — `analyses/results/q01_applications.sql` |
| 2 | Valid loans, total GMV in USD | **27,955** loans · **8,780,942.16 USD** | `silver.fct_loan` — `q02_loans_gmv.sql` |
| 3 | 2026-01 disbursement cohort | **1,540** loans · **473,272.15 USD** | `silver.fct_loan` (= `gold.agg_merchant_monthly`) — `q03_cohort_2026_01.sql` |
| 4 | FPD30 global · 2026-01 cohort | **8.8796 %** (2,204 / 24,821) · **7.7922 %** (120 / 1,540) | `gold.dm_loan_delinquency_snapshot` — `q04_fpd30.sql` |
| 5 | PAR30 and outstanding balance at 2026-06-30 | **20.5008 %** · **2,069,175.39 USD** (424,197.74 USD at DPD > 30) | `gold.dm_loan_delinquency_snapshot` — `q05_par30.sql` |
| 6 | Top 5 merchants by GMV | 1607 (23.49 %), 1397 (7.78 %), 1664 (4.32 %), 1030 (2.36 %), 1286 (1.69 %) = **39.63 %** of GMV | `gold.agg_merchant_monthly` — `q06_top_merchants.sql`, `q06b_concentration.sql` |
| 7 | Real people, redundant customer_ids | **29,093** people · **907** redundant ids (of 30,000) | `silver.dim_customer` — `q07_customers.sql` |

---

## Q1 — Applications

| Measure | Value |
|---|---:|
| Applications in the CDC | 60,000 |
| Deleted (`_op = 'D'`), excluded | 941 |
| **Valid applications** | **59,059** |
| **Approved** (final state) | **33,007** |
| Rejected (final state) | 26,052 |
| Still CREATED | 0 |
| **Global approval rate** | **55.8882 %** |

Final state = latest CDC event by business time, ties broken by ingest time (A2). Ordering by
ingest time instead would change the final status of 54 applications (F6). Deleted applications
"did not exist for business purposes" (A3). Approval rate is almost identical by currency:
COP 55.87 %, BRL 55.91 %.

## Q2 — Valid loans and GMV

| Currency | Valid loans | Principal (local) | GMV (USD) | Share |
|---|---:|---:|---:|---:|
| COP | 16,606 | 22,579,937,000.00 | 5,266,459.97 | 59.98 % |
| BRL | 11,349 | 19,214,166.76 | 3,514,482.19 | 40.02 % |
| **Total** | **27,955** | | **8,780,942.16** | 100 % |

A valid loan has an application that exists in the CDC, is not deleted and is APPROVED (A5);
120 delivered loans have no application at all and are excluded as corrupt migration records
(F7). GMV converts each principal at the FX rate of its **Bogotá** disbursement date (A6, A7);
8,223 loans (29.4 %) were disbursed on a day with no published rate and take the last published
one (F12). Principal equals the approved amount for every loan (F8, enforced by test).

## Q3 — 2026-01 cohort

| Source | Loans | GMV (USD) |
|---|---:|---:|
| `silver.fct_loan`, Bogotá month | **1,540** | **473,272.15** |
| `gold.agg_merchant_monthly`, month 2026-01 | 1,540 | 473,272.15 |
| Reference only: UTC month | 1,541 | 475,211.61 |

The difference is a net of two boundary effects (A6): 12 loans disbursed on 2026-01-01 between
00:00 and 05:00 UTC belong to 31 December in Bogotá and leave the cohort, while 11 loans
disbursed on 2026-02-01 before 05:00 UTC belong to 31 January and join it. 1,529 loans are in
January under both clocks.

## Q4 — FPD30

| Scope | Eligible loans | FPD30 loans | of which unpaid | of which paid > 30 days late | **FPD30** |
|---|---:|---:|---:|---:|---:|
| Global | 24,821 | 2,204 | 547 | 1,657 | **8.8796 %** |
| Cohort 2026-01 | 1,540 | 120 | 38 | 82 | **7.7922 %** |

Eligible = first installment whose due date is at least 30 days before the snapshot (A23);
flagged = first installment settled more than 30 days after its due date, or still unsettled
more than 30 days after it. Settlement dates come from the FIFO allocation of loan-level
payments (A21, A22). By cohort month FPD30 stays in a 7.8 %–9.6 % band (see
`evidence/merchant_monthly.md` row 12): first-payment behaviour has been stable across the
whole origination history.

## Q5 — PAR30 and outstanding balance at 2026-06-30

| DPD bucket | Loans | With balance | Outstanding (USD) | Share of outstanding |
|---|---:|---:|---:|---:|
| 0 | 25,098 | 6,208 | 1,424,487.98 | 68.84 % |
| 1–30 | 947 | 947 | 220,489.67 | 10.66 % |
| 31–60 | 292 | 292 | 61,134.74 | 2.95 % |
| 61–90 | 125 | 125 | 25,929.84 | 1.25 % |
| 90+ | 1,493 | 1,493 | 337,133.16 | 16.29 % |
| **Total** | **27,955** | **9,065** | **2,069,175.39** | 100 % |

**PAR30 = 424,197.74 / 2,069,175.39 = 20.5008 %** (1,910 loans with DPD > 30). FX at the
snapshot date: COP 4,141.00 and BRL 5.6113 per USD (A12). By currency: COP 19.79 %, BRL 21.67 %.

Outstanding balance = sum of `amount_due` of every installment not settled as of the date,
overdue or not yet due (A11, the README's literal definition). DPD = days since the due date of
the oldest installment strictly past due (A24). Sensitivity of the open definitions:

| Variant | Outstanding (USD) | PAR30 |
|---|---:|---:|
| Primary (gross balance, snapshot-date FX) | 2,069,175.39 | 20.5008 % |
| Net of partial payments (A11 alternative) | 2,057,634.75 | 20.5683 % |
| At each loan's disbursement-date FX (A12 alternative) | 2,047,237.02 | 20.4910 % |

Two readings matter more than the decimals. First, **PAR30 is a vintage story**: 77.88 % for
loans disbursed in 2025 versus 6.43 % for 2026 loans. The old book is what remains unpaid; the
young book is mostly not yet due. Second, **nothing is ever written off in this data**: loans in
the 90+ bucket (1,493 of them, 16.29 % of the balance) stay in numerator and denominator
forever, so the portfolio PAR30 rises monotonically from 0 % in January 2025 to 20.5 % in June
2026 (`evidence/merchant_monthly.md` row 11). A PAR30 without a write-off policy measures
accumulated history, not current credit quality; a 90+-day charge-off rule would be the first
thing to agree with Risk before publishing it as a KPI.

## Q6 — Top 5 merchants by GMV, and what the distribution says

| Rank | Merchant | Country | Category (current) | Loans | GMV (USD) | Share | Approval | FPD30 | PAR30 at snapshot |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 1607 | BR | EDUCATION | 6,675 | 2,062,698.44 | 23.49 % | 56.05 % | 9.63 % | 21.51 % |
| 2 | 1397 | CO | HEALTH | 2,184 | 683,302.34 | 7.78 % | 55.27 % | 8.54 % | 20.42 % |
| 3 | 1664 | CO | HEALTH | 1,207 | 379,017.69 | 4.32 % | 56.55 % | 8.10 % | 17.21 % |
| 4 | 1030 | CO | FASHION | 609 | 206,931.64 | 2.36 % | 54.41 % | 8.24 % | 16.23 % |
| 5 | 1286 | CO | TRAVEL | 477 | 148,238.13 | 1.69 % | 53.99 % | 10.05 % | 22.87 % |
| | **Top 5** | | | | **3,480,188** | **39.63 %** | | 9.20 % | 20.53 % |
| | Other 693 | | | | 5,300,754 | 60.37 % | | 8.67 % | 20.48 % |

Concentration: the top 20 merchants are 53.86 % of GMV; **15 merchants make half of it and 141
make 80 %**; the remaining 680 merchants (rank 21–698) share 46 %. By country, Brazil is 28 % of
the merchants (196 of 700) but 40.02 % of GMV and 37.88 % of the outstanding balance, almost
entirely because of merchant 1607.

**What this says about the business.** Lumo is a long-tail BNPL network anchored on one
partner: a single Brazilian education merchant originates almost a quarter of all volume, and
its book performs slightly worse than the rest (FPD30 9.63 % vs 8.67 %, PAR30 21.51 % vs
20.48 %). Approval rates are strikingly uniform, 54–57 % for every large merchant and 55.9 % in
both currencies, which points to one global credit policy rather than merchant-specific
underwriting; the risk differentiation appears after approval, in repayment. Forty percent of
USD-reported GMV carries BRL exposure (the BRL moved between 5.07 and 5.80 per USD over the
period, a ±7 % swing), so part of any USD growth trend is FX, not volume.

**What this says about concentration risk in the metrics themselves.**

- *Headline rates are weighted averages dominated by one book.* Removing merchant 1607 moves
  portfolio FPD30 from 8.88 % to 8.64 % and PAR30 from 20.50 % to 20.21 %. Modest today, but any
  change in that merchant's mix, pricing or collections moves every global number, and a
  reviewer comparing "portfolio" FPD30 across months is largely watching one merchant.
- *Category views are fragile.* Merchant 1607 has a single SCD2 version; a renegotiation of
  its category would move 23 % of GMV from EDUCATION to another category overnight. The
  point-in-time rule (A14, A25) already matters for 8.16 % of applications; without it, category
  trends would be rewritten every time a large merchant changes category.
- *PAR30 rewards young books.* Because nothing is written off, a merchant that started in 2025
  looks worse than one that started in 2026 regardless of underwriting (77.88 % vs 6.43 % by
  vintage). Merchant PAR30 must be read alongside vintage, or after a write-off policy exists.
  The cohort variant published in `agg_merchant_monthly` (`par30_cohort_rate_at_snapshot`)
  shows the other extreme: 1607's June 2026 cohort has 0.0 % PAR30 simply because it is new.
- *Small denominators.* 680 merchants share 46 % of GMV; their monthly FPD30 and PAR30 sit on
  tens of loans and swing on single defaults. Rates in `agg_merchant_monthly` are published with
  their numerators and denominators for that reason, and are NULL when the denominator is 0.
- *Unclassified volume.* 11 merchants were never given a category (F17, A17): 237 loans
  (0.85 % of the book) sit under UNKNOWN in every category breakdown rather than being dropped.

## Q7 — Real people and redundant customer_ids

| Measure | Value |
|---|---:|
| customer_ids in the master | 30,000 |
| **Real people** (distinct `document_number`, A1) | **29,093** |
| **Redundant customer_ids** | **907** |
| People holding two ids (no one holds more) | 907 |
| of which with ids in two countries | 346 |
| of which with different birth years across ids | 884 |
| Alternative identity `document_number + country`: people / redundant | 29,439 / 561 |

The data dictionary states that a person's legal identity is the `document_number`, so that is
the published answer. The 346 documents that appear under both CO and BR with different birth
years are flagged on `dim_customer` (`has_cross_country_ids`) rather than silently merged or
split; the alternative count is shown so the reader can judge. The mapping from every
customer_id to its person is `bridge_customer_person`, and the arithmetic (30,000 = sum of ids
over people) is enforced by `assert_person_counts_reconcile`.

---

## Reading guide

| Document | What it holds |
|---|---|
| `ASSUMPTIONS.md` | A1–A25 business definitions with rationale and alternatives; F1–F18 data quality findings with DMBOK dimension, treatment and test |
| `DATA_JOURNEY.md` | Row-count funnel per extract with the reason for every delta; one row per build step; error ledger; conclusions revised along the way |
| `DATA_QUALITY.md` | DMBOK matrix generated from the manifest and the run results: 244 tests across 7 dimensions, 30 of 30 models covered |
| `AI_LOG.md` | What was delegated to the AI assistant and what was not, decisive prompts, eight cases where it was wrong, and how the numbers were verified |
| `WORKLOG.md` | Step-by-step trace with commands, results and commits |
| `evidence/` | Outputs of every profiling and result query, the cross-check, the dbt artefacts and the build log |
