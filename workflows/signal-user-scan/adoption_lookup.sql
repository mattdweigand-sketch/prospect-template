-- Fictional interface example: prospect_source views are not installed. Configure a reviewed private query copy before live use.
-- signal-user-scan. One row of org-level adoption facts for one CRM Account.
-- Bindings, 1-based: ?1 configured CRM's opaque Account ID (represented according to the reviewed warehouse mapping), ?2 account email domain (lowercase, no @), ?3 snapshot_date (policy warehouse.data_date, YYYY-MM-DD).
-- Returns 7 of the 11 policy user_scan.bundle_keys. The skill adds account_name, crm_account_id, account_domain, and derives adoption.
-- org_service_types and org_platforms are comma-joined strings. Empty string means none, the skill splits to an empty list.
-- Counts only organizations with is_deleted = FALSE, the same set the booleans read.
-- Returns booleans and categories only. Never add user ids, emails, names, counts of people, or activity timestamps.
WITH acct AS (
  SELECT ? AS crm_account_id, LOWER(?) AS domain, TO_DATE(?) AS snapshot_date
),
org_map AS (
  SELECT i.organization_uuid, o.service_type
  FROM prospect_source.organization_account_map i
  JOIN prospect_source.organizations o
    ON o.organization_uuid = i.organization_uuid AND o.is_deleted = FALSE
  JOIN acct ON i.crm_account_id = acct.crm_account_id
  WHERE i.is_unambiguous
),
org_sub AS (
  SELECT s.organization_uuid, m.service_type, s.is_subscribed, s.is_paying, s.subscription_platform
  FROM prospect_source.organization_subscription_daily s
  JOIN org_map m ON m.organization_uuid = s.organization_uuid
  JOIN acct ON s.snapshot_date = acct.snapshot_date
),
individuals AS (
  SELECT COUNT(*) > 0 AS paid_individuals_exist
  FROM prospect_source.paid_individual_subscription_daily d
  JOIN prospect_source.user_domains u ON u.user_id = d.user_id
  JOIN acct ON d.snapshot_date = acct.snapshot_date AND LOWER(u.email_domain) = acct.domain
  WHERE d.is_paying = TRUE
)
SELECT
  (SELECT TO_CHAR(snapshot_date, 'YYYY-MM-DD') FROM acct)                  AS data_through_date,
  (SELECT COUNT(*) FROM org_map)                                     AS mapped_org_count,
  COALESCE((SELECT BOOLOR_AGG(is_subscribed) FROM org_sub), FALSE)   AS org_subscribed,
  COALESCE((SELECT BOOLOR_AGG(is_paying) FROM org_sub), FALSE)       AS org_paying,
  COALESCE((SELECT LISTAGG(DISTINCT service_type, ',') FROM org_sub), '')          AS org_service_types,
  COALESCE((SELECT LISTAGG(DISTINCT subscription_platform, ',') FROM org_sub), '') AS org_platforms,
  (SELECT paid_individuals_exist FROM individuals)                   AS paid_individuals_exist
