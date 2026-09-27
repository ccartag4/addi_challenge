"""
Independent cross-check of the RESULTS.md figures.

Everything here is recomputed from the RAW CSV extracts with pandas: no dbt model is read to
produce a number. The business rules follow ASSUMPTIONS.md (A1-A25) but the code path is
different on purpose:
  * timestamps parsed by a separate function, Bogotá dates via pandas tz conversion
  * CDC resolved by sorting and taking the last row per application
  * FIFO allocation as an explicit per-loan loop over payments and installments, in integer
    cents (the SQL version is an interval-overlap join)
Only at the end are the pandas figures compared with the gold/silver models in lumo.duckdb
(opened read-only), including a loan-by-loan comparison of DPD and outstanding balance.

Usage (from deliverables/, after `dbt build`):
    python scripts/crosscheck_pandas.py [--data ../data] [--db lumo.duckdb] [--snapshot 2026-06-30]
                                        [--out evidence/crosscheck_pandas.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import decimal
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
PLACEHOLDER_CUSTOMER = "999999999"
TZ = "America/Bogota"


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def parse_utc(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns, UTC]")
    is_epoch = s.str.fullmatch(r"\d{13}")
    out[is_epoch] = pd.to_datetime(s[is_epoch].astype("int64"), unit="ms", utc=True)
    out[~is_epoch] = pd.to_datetime(s[~is_epoch], utc=True, format="mixed", errors="coerce")
    return out


def bogota_date(ts: pd.Series) -> pd.Series:
    """UTC timestamps -> naive Timestamp at Bogotá midnight (a 'date' that stays vectorised)."""
    return ts.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()


def cents(x: pd.Series) -> pd.Series:
    return (pd.to_numeric(x, errors="coerce") * 100).round().astype("int64")


def md_table(columns, rows):
    cells = [[("" if v is None else str(v)) for v in r] for r in rows]
    w = [max(len(str(c)), *(len(r[i]) for r in cells)) if cells else len(str(c)) for i, c in enumerate(columns)]
    fmt = "| " + " | ".join(f"{{:<{x}}}" for x in w) + " |"
    return "\n".join([fmt.format(*columns), "|" + "|".join("-" * (x + 2) for x in w) + "|"] + [fmt.format(*r) for r in cells])


# ----------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(PROJECT / ".." / "data"))
    ap.add_argument("--db", default=str(PROJECT / "lumo.duckdb"))
    ap.add_argument("--snapshot", default="2026-06-30")
    ap.add_argument("--out", default="evidence/crosscheck_pandas.md")
    args = ap.parse_args()

    data = Path(args.data)
    snapshot = pd.Timestamp(args.snapshot)
    read = lambda name: pd.read_csv(data / f"{name}.csv", dtype=str, keep_default_na=True)

    # ---------------- applications (A2, A3, A4) ----------------
    a = read("raw_applications_cdc").drop_duplicates()
    a["ev"] = parse_utc(a["event_at_utc"])
    a["ing"] = parse_utc(a["_ingested_at_utc"])
    a["op_rank"] = a["_op"].map({"I": 0, "U": 1, "D": 2})
    a["is_placeholder"] = a["customer_id"] == PLACEHOLDER_CUSTOMER
    a = a.drop_duplicates(subset=["application_id", "customer_id", "merchant_id", "requested_amount", "currency",
                                  "status", "approved_amount", "ev", "ing", "_op"])
    a = a.sort_values(["application_id", "ev", "ing", "op_rank", "is_placeholder"], ascending=[True, True, True, True, False])
    last = a.groupby("application_id").tail(1).set_index("application_id")
    deleted = set(a.loc[a["_op"] == "D", "application_id"])
    last["is_valid"] = ~last.index.isin(deleted)
    last["is_approved"] = last["is_valid"] & (last["status"] == "APPROVED")
    real_customer = a.loc[~a["is_placeholder"]].groupby("application_id")["customer_id"].max()
    last["customer_id_resolved"] = real_customer.reindex(last.index)
    q1 = dict(valid=int(last["is_valid"].sum()), approved=int(last["is_approved"].sum()))
    q1["rate_pct"] = round(100.0 * q1["approved"] / q1["valid"], 4)

    # ---------------- FX daily calendar (A7) ----------------
    fx = read("raw_fx_rates")
    fx["d"] = pd.to_datetime(fx["rate_date"])
    fx["r"] = fx["units_per_usd"].astype(float)
    fxw = fx.pivot(index="d", columns="currency", values="r")
    fxw = fxw.reindex(pd.date_range(fxw.index.min(), max(fxw.index.max(), snapshot))).ffill()

    def rate(dates: pd.Series, ccy: pd.Series) -> np.ndarray:
        return np.array([fxw.at[d, c] for d, c in zip(dates, ccy)])

    # ---------------- loans (A5, A6) ----------------
    l = read("raw_loans")
    l["disb"] = parse_utc(l["disbursed_at_utc"])
    l["disb_date"] = bogota_date(l["disb"])
    approved_ids = set(last.index[last["is_approved"]])
    vl = l[l["application_id"].isin(approved_ids)].copy()
    vl["principal_f"] = vl["principal"].astype(float)
    vl["gmv_usd"] = vl["principal_f"] / rate(vl["disb_date"], vl["currency"])
    vl["month"] = vl["disb_date"].dt.to_period("M").astype(str)
    q2 = dict(loans=len(vl), gmv=round(vl["gmv_usd"].sum(), 2))
    c26 = vl[vl["month"] == "2026-01"]
    q3 = dict(loans=len(c26), gmv=round(c26["gmv_usd"].sum(), 2))

    # ---------------- installments ----------------
    i = read("raw_installments")
    i = i[i["loan_id"].isin(vl["loan_id"])].copy()
    i["due"] = pd.to_datetime(i["due_date"])
    i["due_c"] = cents(i["amount_due"])
    i["n"] = i["installment_number"].astype(int)

    # ---------------- payments (A8, A9, A10) ----------------
    p = read("raw_payments").drop_duplicates()
    p["paid"] = parse_utc(p["paid_at_utc"])
    p["amt_c"] = cents(p["amount_raw"])
    p.loc[p["source_system"] == "legacy_v1", "amt_c"] = (p.loc[p["source_system"] == "legacy_v1", "amt_c"] / 100).round().astype("int64")
    p["loan_id"] = p["loan_ref"].str.extract(r"(\d+)$")[0]
    p = p.drop_duplicates(subset=["payment_id", "loan_id", "paid", "amt_c", "source_system", "payment_method", "status", "reversed_payment_id"])
    voided = set(p.loc[p["status"] == "REVERSED", "reversed_payment_id"].dropna())
    eff = p[(p["status"] == "SETTLED") & (~p["payment_id"].isin(voided)) & (p["loan_id"].isin(vl["loan_id"]))].copy()
    eff["paid_date"] = bogota_date(eff["paid"])
    eff_asof = eff[eff["paid_date"] <= snapshot].sort_values(["loan_id", "paid", "payment_id"])
    n_effective_all = len(eff)

    # ---------------- FIFO as an explicit loop (A21-A24), integer cents ----------------
    inst_by_loan: dict[str, list] = defaultdict(list)
    for loan_id, due, due_c, n in zip(i["loan_id"], i["due"], i["due_c"], i["n"]):
        inst_by_loan[loan_id].append((due, n, int(due_c)))
    for v in inst_by_loan.values():
        v.sort()
    pay_by_loan: dict[str, list] = defaultdict(list)
    for loan_id, d, c in zip(eff_asof["loan_id"], eff_asof["paid_date"], eff_asof["amt_c"]):
        pay_by_loan[loan_id].append((d, int(c)))

    rows = []           # per installment: loan_id, n, due, due_c, paid_c, settled_date
    loan_rows = []      # per loan: loan_id, outstanding_c, dpd
    thirty = pd.Timedelta(days=30)
    for loan_id, ccy in zip(vl["loan_id"], vl["currency"]):
        insts = inst_by_loan[loan_id]
        paid_c = [0] * len(insts)
        settled = [None] * len(insts)
        k = 0
        for pdate, amount in pay_by_loan.get(loan_id, []):
            remaining = amount
            while remaining > 0 and k < len(insts):
                need = insts[k][2] - paid_c[k]
                take = min(need, remaining)
                paid_c[k] += take
                remaining -= take
                if paid_c[k] == insts[k][2]:
                    settled[k] = pdate
                    k += 1
            # remaining > 0 here = overpayment beyond the plan: left unallocated
        outstanding_c = 0
        oldest_overdue = None
        for (due, n, due_c), pc, sd in zip(insts, paid_c, settled):
            rows.append((loan_id, n, due, due_c, pc, sd))
            if sd is None:
                outstanding_c += due_c
                if due < snapshot and (oldest_overdue is None or due < oldest_overdue):
                    oldest_overdue = due
        dpd = (snapshot - oldest_overdue).days if oldest_overdue is not None else 0
        loan_rows.append((loan_id, ccy, outstanding_c, dpd))

    inst = pd.DataFrame(rows, columns=["loan_id", "n", "due", "due_c", "paid_c", "settled"])
    first = inst[inst["n"] == 1].merge(vl[["loan_id", "month"]], on="loan_id")
    first["eligible"] = first["due"] <= snapshot - thirty
    late_paid = first["settled"].notna() & ((first["settled"] - first["due"]) > thirty)
    unpaid_late = first["settled"].isna() & ((snapshot - first["due"]) > thirty)
    first["fpd30"] = first["eligible"] & (late_paid | unpaid_late)
    q4 = dict(eligible=int(first["eligible"].sum()), flagged=int(first["fpd30"].sum()))
    q4["rate_pct"] = round(100.0 * q4["flagged"] / q4["eligible"], 4)
    f26 = first[first["month"] == "2026-01"]
    q4c = dict(eligible=int(f26["eligible"].sum()), flagged=int(f26["fpd30"].sum()))
    q4c["rate_pct"] = round(100.0 * q4c["flagged"] / q4c["eligible"], 4)

    ls = pd.DataFrame(loan_rows, columns=["loan_id", "currency", "outstanding_c", "dpd"])
    ls["outstanding_local"] = ls["outstanding_c"] / 100.0
    ls["outstanding_usd"] = ls["outstanding_local"] / rate(pd.Series([snapshot] * len(ls)), ls["currency"])
    q5 = dict(outstanding=round(ls["outstanding_usd"].sum(), 2),
              par30_num=round(ls.loc[ls["dpd"] > 30, "outstanding_usd"].sum(), 2))
    q5["par30_pct"] = round(100.0 * q5["par30_num"] / q5["outstanding"], 4)

    # ---------------- top merchants (Q6) and customers (Q7) ----------------
    top = vl.groupby("merchant_id")["gmv_usd"].sum().sort_values(ascending=False)
    q6 = [(m, round(g, 2), round(100 * g / top.sum(), 2)) for m, g in top.head(5).items()]
    c = read("raw_customers")
    doc = c["document_number"].str.strip()
    q7 = dict(ids=len(c), people=int(doc.nunique()), alt=int((doc + "|" + c["country"].str.strip()).nunique()))
    q7["redundant"] = q7["ids"] - q7["people"]

    # ---------------- dbt side (read-only) ----------------
    con = duckdb.connect(args.db, read_only=True)

    def one(sql: str) -> tuple:
        # DuckDB returns decimal.Decimal for DECIMAL columns; normalise to float for comparisons
        return tuple(float(v) if isinstance(v, decimal.Decimal) else v for v in con.sql(sql).fetchone())
    d_q1 = one("select count(*) filter (where is_valid), count(*) filter (where is_approved) from silver.fct_application")
    d_q2 = one("select count(*), round(sum(principal_usd), 2) from silver.fct_loan")
    d_q3 = one("select count(*), round(sum(principal_usd), 2) from silver.fct_loan where disbursed_month = date '2026-01-01'")
    d_q4 = one("select count(*) filter (where is_fpd30_eligible), count(*) filter (where is_fpd30) from gold.dm_loan_delinquency_snapshot")
    d_q4c = one("select count(*) filter (where is_fpd30_eligible), count(*) filter (where is_fpd30) from gold.dm_loan_delinquency_snapshot where disbursed_month = date '2026-01-01'")
    d_q5 = one("select round(sum(outstanding_usd), 2), round(sum(outstanding_usd) filter (where is_par30), 2) from gold.dm_loan_delinquency_snapshot")
    d_q6 = [(str(m), float(g)) for m, g in con.sql("select merchant_id, round(sum(principal_usd), 2) from silver.fct_loan group by 1 order by 2 desc limit 5").fetchall()]
    d_q7 = one("select (select count(*) from silver.stg_customers), (select count(*) from silver.dim_customer)")
    d_eff = one("select count(*) from silver.fct_payment")[0]
    d_snap = con.sql("select cast(loan_id as varchar) loan_id, dpd, outstanding_local from gold.dm_loan_delinquency_snapshot").df()

    # loan-by-loan comparison
    cmp = ls.merge(d_snap, on="loan_id", how="outer", suffixes=("_pd", "_dbt"), indicator=True)
    only_one_side = int((cmp["_merge"] != "both").sum())
    dpd_mismatch = int((cmp["dpd_pd"] != cmp["dpd_dbt"]).sum())
    bal_mismatch = int(((cmp["outstanding_local_pd"] - cmp["outstanding_local_dbt"]).abs() > 0.005).sum())

    # ---------------- report ----------------
    def line(q, what, pv, dv, tol=0.0):
        try:
            ok = abs(float(pv) - float(dv)) <= tol
        except (TypeError, ValueError):
            ok = str(pv) == str(dv)
        return (q, what, pv, dv, "✅" if ok else "❌")

    checks = [
        line("Q1", "valid applications", q1["valid"], d_q1[0]),
        line("Q1", "approved applications", q1["approved"], d_q1[1]),
        line("Q1", "approval rate %", q1["rate_pct"], round(100.0 * d_q1[1] / d_q1[0], 4), 1e-4),
        line("Q2", "valid loans", q2["loans"], d_q2[0]),
        line("Q2", "GMV USD", f"{q2['gmv']:,.2f}", f"{d_q2[1]:,.2f}", 0.01),
        line("Q3", "2026-01 loans", q3["loans"], d_q3[0]),
        line("Q3", "2026-01 GMV USD", f"{q3['gmv']:,.2f}", f"{d_q3[1]:,.2f}", 0.01),
        line("Q4", "FPD30 eligible (global)", q4["eligible"], d_q4[0]),
        line("Q4", "FPD30 flagged (global)", q4["flagged"], d_q4[1]),
        line("Q4", "FPD30 % (global)", q4["rate_pct"], round(100.0 * d_q4[1] / d_q4[0], 4), 1e-4),
        line("Q4", "FPD30 eligible (2026-01)", q4c["eligible"], d_q4c[0]),
        line("Q4", "FPD30 flagged (2026-01)", q4c["flagged"], d_q4c[1]),
        line("Q4", "FPD30 % (2026-01)", q4c["rate_pct"], round(100.0 * d_q4c[1] / d_q4c[0], 4), 1e-4),
        line("Q5", "outstanding USD", f"{q5['outstanding']:,.2f}", f"{d_q5[0]:,.2f}", 0.01),
        line("Q5", "PAR30 numerator USD", f"{q5['par30_num']:,.2f}", f"{d_q5[1]:,.2f}", 0.01),
        line("Q5", "PAR30 %", q5["par30_pct"], round(100.0 * d_q5[1] / d_q5[0], 4), 1e-4),
        line("Q6", "top 5 merchants (id: GMV USD)", " | ".join(f"{m}: {g:,.0f}" for m, g, _ in q6), " | ".join(f"{m}: {g:,.0f}" for m, g in d_q6)),
        line("Q7", "customer_ids", q7["ids"], d_q7[0]),
        line("Q7", "real people", q7["people"], d_q7[1]),
        line("Q7", "redundant ids", q7["redundant"], d_q7[0] - d_q7[1]),
        line("—", "effective payments", n_effective_all, d_eff),
        line("—", "loans present on one side only", 0, only_one_side),
        line("—", "loans with a different DPD", 0, dpd_mismatch),
        line("—", "loans with a different balance", 0, bal_mismatch),
    ]
    # the string-formatted USD comparisons: compare numerically
    for idx, ch in enumerate(checks):
        q, what, pv, dv, ok = ch
        if isinstance(pv, str) and pv.replace(",", "").replace(".", "").isdigit():
            good = abs(float(pv.replace(",", "")) - float(dv.replace(",", ""))) <= 0.01
            checks[idx] = (q, what, pv, dv, "✅" if good else "❌")

    n_ok = sum(1 for ch in checks if ch[4] == "✅")
    report = [
        "# Independent cross-check — pandas from raw CSVs vs dbt gold/silver",
        "",
        f"Generated {dt.datetime.now():%Y-%m-%d %H:%M} by `scripts/crosscheck_pandas.py`. Snapshot {args.snapshot}. "
        f"pandas {pd.__version__}. {n_ok} of {len(checks)} checks match.",
        "",
        "The pandas column is computed from the raw CSV extracts only (own parser, own CDC resolution, own FIFO "
        "loop in integer cents). The dbt column is read from the warehouse. Tolerances: 0.01 USD on sums, "
        "0.0001 on percentages, exact on counts.",
        "",
        md_table(["Q", "Measure", "pandas (raw CSVs)", "dbt (warehouse)", "match"], checks),
        "",
        "## Notes",
        "",
        f"- Applications resolved: {len(last):,} (deleted {len(deleted):,}); valid loans: {len(vl):,}; installments: {len(inst):,}; "
        f"effective payments on or before the snapshot: {len(eff_asof):,}.",
        f"- Alternative Q7 identity (document + country): {q7['alt']:,} people, {q7['ids'] - q7['alt']:,} redundant ids.",
        f"- Loan-by-loan: {len(cmp):,} loans compared on DPD and outstanding balance.",
    ]
    out = PROJECT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(f"{q:>3} {what:<32} pandas={pv!s:<28} dbt={dv!s:<28} {ok}" for q, what, pv, dv, ok in checks))
    print(f"\n{n_ok} of {len(checks)} checks match. Wrote {out.relative_to(PROJECT)}")
    return 0 if n_ok == len(checks) else 2


if __name__ == "__main__":
    sys.exit(main())
