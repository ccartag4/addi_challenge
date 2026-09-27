-- Q2. How many valid loans were disbursed, and what is total GMV in USD?
-- Source: silver.fct_loan (A5 validity, A6 Bogotá dates, A7 FX at disbursement date).
select
    coalesce(currency, 'TOTAL')                         as currency,
    count(*)                                            as valid_loans,
    round(sum(principal), 2)                            as principal_local,
    round(sum(principal_usd), 2)                        as gmv_usd,
    round(100.0 * sum(principal_usd)
              / (select sum(principal_usd) from {{ ref('fct_loan') }}), 2) as share_of_gmv_pct
from {{ ref('fct_loan') }}
group by rollup (currency)
order by currency nulls last
