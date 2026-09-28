-- Fictional interface example: prospect_source views are not installed. Configure a reviewed private query copy before live use.
-- signal-prospector adoption source. Accounts the caller owns on the Salesforce replica, inside the headcount band, where
-- paying individual Example Research users share the Account's web domain and no organization subscription exists on date_pt.
-- Bindings, 1-based: ?1 date_pt (policy warehouse.data_date, YYYY-MM-DD, TEXT), ?2 Salesforce owner id (TEXT, policy identity.sfdc_user_id),
--                    ?3 min employees (FIXED, icp.md territory.min_employees), ?4 max employees (FIXED, icp.md territory.max_employees),
--                    ?5 row limit (FIXED, policy prospector.adoption_source.candidate_rows).
-- The owner filter uses the replica so the rows are the caller's Accounts. Live Salesforce still decides open-deal status, the replica lags.
-- Returns org-level booleans and the Account's own Salesforce fields only. Never add user ids, user emails, names, seat counts,
-- query content, or activity timestamps. A row is one tier2 paid_individuals_present signal. It admits an account only beside one web
-- tier2 signal, per signals.md admission, enforced by route_candidate.py.
-- account_domain is lowercased before the scheme, www., and path are stripped, so HTTPS://Acme.example and https://acme.example match the same email domain.
WITH p AS (
  SELECT TO_DATE(?) AS date_pt, ? AS owner_id, ? AS min_emp, ? AS max_emp
), live_accounts AS (
  SELECT a.id AS salesforce_account_id,
         a.name AS account_name,
         a.owner_id,
         a.number_of_employees,
         REGEXP_REPLACE(REGEXP_REPLACE(LOWER(TRIM(a.website)), '^https?://', ''), '^www\\.|[/:?#].*$', '') AS account_domain
  FROM prospect_source.account a
  WHERE a.is_deleted = FALSE
    AND NULLIF(TRIM(a.website), '') IS NOT NULL
), owned AS (
  SELECT a.* FROM live_accounts a CROSS JOIN p
  WHERE a.owner_id = p.owner_id
    AND a.number_of_employees BETWEEN p.min_emp AND p.max_emp
), domains AS (
  SELECT account_domain
  FROM live_accounts
  WHERE account_domain <> '' AND account_domain NOT LIKE '%@%'
  GROUP BY account_domain
  HAVING COUNT(*) = 1                                             -- one Account per domain, otherwise the join would guess
), paid AS (
  SELECT LOWER(u.email_domain) AS account_domain
  FROM prospect_source.dim_subscription_user_daily d
  JOIN prospect_source.dim_user_attributes u ON u.user_id = d.user_id
  CROSS JOIN p
  WHERE d.date_pt = p.date_pt AND d.is_paying = TRUE
    AND LOWER(u.email_domain) IN (SELECT account_domain FROM domains)
  GROUP BY LOWER(u.email_domain)
), org_sub AS (
  SELECT i.salesforce_account_id, BOOLOR_AGG(COALESCE(s.is_subscribed, FALSE)) AS org_subscribed
  FROM prospect_source.int_organization_salesforce_identity i
  JOIN prospect_source.dim_organizations o
    ON o.organization_uuid = i.organization_uuid AND o.is_deleted = FALSE
  JOIN prospect_source.dim_organization_subscription_daily s ON s.organization_uuid = i.organization_uuid
  CROSS JOIN p
  WHERE i.is_identity_unambiguous AND s.date_pt = p.date_pt
  GROUP BY i.salesforce_account_id
)
SELECT o.salesforce_account_id,
       o.account_name,
       o.account_domain,
       o.number_of_employees,
       TO_CHAR(p.date_pt, 'YYYY-MM-DD') AS data_through_date,
       TRUE AS paid_individuals_exist,
       COALESCE(os.org_subscribed, FALSE) AS org_subscribed
FROM owned o
JOIN domains dm ON dm.account_domain = o.account_domain
JOIN paid pd ON pd.account_domain = o.account_domain
LEFT JOIN org_sub os ON os.salesforce_account_id = o.salesforce_account_id
CROSS JOIN p
WHERE COALESCE(os.org_subscribed, FALSE) = FALSE
ORDER BY o.number_of_employees DESC, o.salesforce_account_id
LIMIT ?
