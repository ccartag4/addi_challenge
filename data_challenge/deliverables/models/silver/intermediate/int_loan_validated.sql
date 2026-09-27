-- Silver / intermediate. Grain: one row per loan as delivered (28,075), with the validity
-- verdict (A5) and the reason when excluded, so fct_loan's filter is auditable:
--   NO_APPLICATION            application_id absent from the CDC (F7: 120 corrupt migration rows)
--   APPLICATION_DELETED       application has a CDC delete (A3; none observed)
--   APPLICATION_NOT_APPROVED  final status is not APPROVED (none observed)
with loans as (
    select * from {{ ref('stg_loans') }}
),

apps as (
    select
        application_id,
        customer_id         as app_customer_id,
        merchant_id         as app_merchant_id,
        currency            as app_currency,
        requested_amount,
        approved_amount,
        created_date        as application_created_date,
        is_deleted          as app_is_deleted,
        is_approved         as app_is_approved
    from {{ ref('fct_application') }}
)

select
    l.*,
    a.app_customer_id,
    a.app_merchant_id,
    a.app_currency,
    a.requested_amount,
    a.approved_amount,
    a.application_created_date,
    case
        when a.application_id is null   then 'NO_APPLICATION'
        when a.app_is_deleted           then 'APPLICATION_DELETED'
        when not a.app_is_approved      then 'APPLICATION_NOT_APPROVED'
    end                                                     as exclusion_reason,
    (a.application_id is not null and a.app_is_approved)    as is_valid
from loans l
left join apps a using (application_id)
