-- Q5. PAR30 as of 2026-06-30 and total outstanding balance in USD at that date (A11, A12).
-- Source: gold.dm_loan_delinquency_snapshot. Rows: one per DPD bucket plus the total.
select
    coalesce(dpd_bucket, 'TOTAL')                                                       as dpd_bucket,
    count(*)                                                                            as loans,
    count(*) filter (where outstanding_local > 0)                                       as loans_with_balance,
    round(sum(outstanding_usd), 2)                                                      as outstanding_usd,
    round(100.0 * sum(outstanding_usd)
              / (select sum(outstanding_usd) from {{ ref('dm_loan_delinquency_snapshot') }}), 2) as share_of_outstanding_pct,
    round(sum(outstanding_usd) filter (where is_par30), 2)                              as par30_outstanding_usd,
    round(100.0 * sum(outstanding_usd) filter (where is_par30) / sum(outstanding_usd), 4) as par30_pct
from {{ ref('dm_loan_delinquency_snapshot') }}
group by rollup (dpd_bucket)
order by case dpd_bucket when '0' then 0 when '1-30' then 1 when '31-60' then 2 when '61-90' then 3 when '90+' then 4 else 5 end
