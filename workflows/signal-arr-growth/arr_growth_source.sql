-- Fictional interface example: prospect_source views are not installed. Configure a reviewed private query copy before live use.
-- signal-arr-growth. Self-serve organizations each mapped unambiguously to a Salesforce Account, ranked by net ARR change.
-- More than one organization may map to an Account. arr_growth_gate.py selects only its first eligible ranked row.
-- Bindings, 1-based: ?1 data_through_date (policy warehouse.data_date, YYYY-MM-DD, TEXT), ?2 window_days (FIXED, policy arr_growth.window_days),
--                    ?3 Salesforce owner id (TEXT, policy identity.sfdc_user_id), ?4 row limit (FIXED, policy arr_growth.candidate_rows).
-- The owner filter uses the Salesforce replica so the ranked rows are the caller's Accounts. Live Salesforce still decides the route, the replica lags.
-- Returns organization-level figures and the Stripe billing email only. Never add user ids, user emails, names, seat counts, or per-user rows.
-- An org needs window_days + 1 daily snapshots, one row per day, each with an ARR value. A missing or duplicated day drops the org from the
-- result. Nothing is zero-filled. Dropped orgs are not reported, so zero rows is a finding, never proof that nothing grew.
WITH p AS (
  SELECT TO_DATE(?) AS through_date, ? AS window_days
), win AS (
  SELECT through_date, window_days, DATEADD(day, -window_days, through_date) AS baseline_date FROM p
), orgs AS (
  SELECT organization_uuid,
         MAX(NULLIF(TRIM(stripe_customer_email), '')) AS billing_email,
         BOOLAND_AGG(COALESCE(product_communications_enabled, FALSE)) AS communications_enabled
  FROM prospect_source.dim_organizations
  WHERE is_deleted = FALSE
  GROUP BY organization_uuid
  HAVING COUNT(*) = 1 AND MAX(UPPER(TRIM(service_type))) = 'SELF_SERVE'
), owned AS (
  SELECT id AS salesforce_account_id FROM prospect_source.account WHERE is_deleted = FALSE AND owner_id = ?
), ident AS (
  SELECT x.organization_uuid, MAX(x.salesforce_account_id) AS salesforce_account_id
  FROM prospect_source.int_organization_salesforce_identity x
  JOIN owned w ON w.salesforce_account_id = x.salesforce_account_id
  WHERE x.is_identity_unambiguous AND x.salesforce_account_id IS NOT NULL
  GROUP BY x.organization_uuid
  HAVING COUNT(*) = 1
), daily AS (
  SELECT s.organization_uuid, s.date_pt,
         MAX(s.organization_name) AS organization_name,
         MAX(s.subscription_platform) AS subscription_platform,
         COUNT(*) AS row_count,
         ROUND(MAX(s.arr_contribution), 2) AS arr_usd
  FROM prospect_source.dim_organization_subscription_daily s
  JOIN orgs o ON o.organization_uuid = s.organization_uuid
  JOIN ident i ON i.organization_uuid = s.organization_uuid
  CROSS JOIN win
  WHERE s.date_pt BETWEEN win.baseline_date AND win.through_date
  GROUP BY s.organization_uuid, s.date_pt
), totals AS (
  SELECT d.organization_uuid,
         MAX(CASE WHEN d.date_pt = win.through_date THEN d.organization_name END) AS organization_name,
         MAX(CASE WHEN d.date_pt = win.through_date THEN d.subscription_platform END) AS subscription_platform,
         MAX(CASE WHEN d.date_pt = win.baseline_date THEN d.arr_usd END) AS baseline_arr_usd,
         MAX(CASE WHEN d.date_pt = win.through_date THEN d.arr_usd END) AS current_arr_usd,
         COUNT(*) AS observed_dates,
         SUM(CASE WHEN d.row_count > 1 OR d.arr_usd IS NULL THEN 1 ELSE 0 END) AS bad_dates,
         MAX(win.window_days) + 1 AS required_dates
  FROM daily d CROSS JOIN win
  GROUP BY d.organization_uuid
)
SELECT t.organization_uuid,
       t.organization_name,
       i.salesforce_account_id,
       TO_CHAR(win.through_date, 'YYYY-MM-DD') AS data_through_date,
       t.baseline_arr_usd,
       t.current_arr_usd,
       ROUND(t.current_arr_usd - t.baseline_arr_usd, 2) AS net_change_usd,
       t.observed_dates,
       t.required_dates,
       t.subscription_platform,
       o.billing_email,
       o.communications_enabled
FROM totals t
JOIN orgs o ON o.organization_uuid = t.organization_uuid
JOIN ident i ON i.organization_uuid = t.organization_uuid
CROSS JOIN win
WHERE t.observed_dates = t.required_dates
  AND t.bad_dates = 0
  AND t.current_arr_usd - t.baseline_arr_usd > 0
ORDER BY net_change_usd DESC, i.salesforce_account_id, t.organization_uuid
LIMIT ?
