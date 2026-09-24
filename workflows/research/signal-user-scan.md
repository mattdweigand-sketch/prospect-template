# Organization adoption scan

Use for aggregate adoption facts about one named, owned CRM account.
This optional workflow requires a reviewed private-data adapter.

## Load / Skip

- Working: output/{run-id}/request.md and its named account.
- Reference: workflows/run.md, _shared/rules.md; policy.json identity and adoption; adapters.md CRM resolution and adoption_lookup contract.
- Skip: public signal search, claims, mail, Slack, billing growth, other accounts and every user-level field. A missing/disabled adapter stops this workflow with an explicit gap.

## Process

1. Resolve one CRM account by supplied ID or name/domain; read ID, name, website, owner/active status and open opportunities. Zero or multiple matches require the user to select an ID. Continue only for identity.owner_id with no open deal; otherwise report `owned_elsewhere` or `active_deal`.
2. Normalize its website to a lowercase domain, removing scheme, www, path and port. Stop for a missing domain or any configured internal domain/subdomain. Confirm the CRM account/domain pair before querying.
3. Use only the configured adoption_lookup adapter, read-only. Bind account ID, normalized domain and the completed data date (today in identity.timezone minus adoption.data_lag_days). For asynchronous queries, wait for confirmed success before reading results. Submission, pending, failure and incomplete pagination never mean no adoption.
4. Expect one aggregate result with explicit mapping coverage. Preserve org subscription/payment booleans, permitted service/platform categories, mapped-org count and paid-individual **presence only**. Split provider comma lists into string arrays. Multiple mapped organizations may be aggregated if the adapter validates their account mapping; ambiguous cross-account mapping stops. No per-person rows may enter chat or artifacts.
5. Build exactly adoption.bundle_keys. Set adoption to org_adopted when org_subscribed is true, otherwise individuals_only if paid_individuals_exist, otherwise none_found. Unknown mapping or coverage yields an explicit unknown finding, not false booleans or an actionable category. Keep source_reference an aggregate query receipt, not a link exposing per-user output.
6. Run `python3 scripts/privacy_check.py --bundle output/RUN_ID/adoption.json`. Exit 0 is required for a clean bundle; fix the offending data on exit 1, never weaken the check. Exit 2 stops. Verify the complete data date and CRM prerequisites independently; the privacy check does not establish those facts.

## Outputs and readiness

The review names account/CRM ID, owner/status, route, domain, data-through date, aggregate subscription and platform/service categories, paid-individual presence, privacy verdict and the exact bundle. Include the query success reference and read time as separate review metadata, outside the bundle's field allowlist. Declare only the aggregate bundle and permitted aggregate receipts as artifacts.

Only the configured adoption.approved_statements entry for the category may be repeated in outreach. There is no outreach statement for none_found or unknown. Explain that none_found covers the supplied mapping/date and is not proof of absence; an organization may be mapped to a duplicate account. There are no effects.

## Human check

Check entity/domain mapping, data date, aggregate-only content and the approved category sentence. Hand off the reviewed bundle by exact run/reference on request; outreach also requires a qualified public signal. Never add names, emails, titles, seats/user counts, queries, activity timestamps or usage trends, even approximately. Do not expand query columns without a separate reviewed adapter/policy change. No provider writes or message wording occur here.
