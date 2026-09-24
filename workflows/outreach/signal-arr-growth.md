# Self-service growth candidates

Manual only. A complete organization revenue series may select owned accounts
for exact fixed-template, unsent drafts to their verified billing addresses.
This optional self-service subscription module requires daily ARR normalized to
USD. It does not apply to transaction revenue or ordinary service fees and is
not a prerequisite for core outreach.

## Load / Skip

- Working: output/{run-id}/request.md and its bounded candidate scope.
- Reference: workflows/run.md, _shared/rules.md; policy.json identity, arr_growth, routing and prospector.headcount_sources; icp.md territory; adapters.md billing_growth, CRM and mail contracts, including reviewed retention.
- Skip: public signal research, adoption/user data, claims, source repositories and unrelated billing records. Disabled or unconfigured billing/template/retention stops this workflow.

## Process

1. Run only the configured read-only billing_growth adapter, binding completed data date (identity.timezone today minus data_lag_days), window_days, owner and candidate_rows. For asynchronous execution, consume rows only after confirmed success. Zero rows is a scoped finding; incomplete/failed data is not zero.
2. The adapter must establish nondeleted self-service organizations, unambiguous account mappings, one valid daily snapshot per required date for window_days + 1 dates, finite nonnegative baseline/current amounts in the declared currency, consistent positive current-minus-baseline change, allowed billing platform and communications permission. Never fill missing dates with zero. Rank descending by net growth, then account ID in ordinary case-sensitive string order; the gate rejects a different order before applying the cap. Raw amounts and billing output remain session-only unless a reviewed private retention policy explicitly permits more.
3. Read CRM accounts in bounded batches by returned account IDs, with name, website, live owner/active status, headcount and all open opportunities. Replica ownership is not authoritative. Only owned accounts routing scan continue. Every open deal holds, including inactive/house owners. Accounts needing claims belong to signal-prospector.
4. Use current CRM employee count when populated; otherwise take the first dated buying-entity headcount source in the configured order. Unknown/out-of-territory holds. For eligible accounts, read all contacts exactly matching billing_email and all account-wide Email/Call tasks and events for the suppression window. Any person on the account counts.
5. Search sent mail to **any recipient at the billing-address domain** for that window. last_touch_date is the latest suppressing CRM/mail date, or null only after complete reads. No-contact is allowed for a team greeting; multiple contacts or an email mismatch holds. Never infer a person's name from their address or switch to a different contact.
6. Build the packet in scripts/arr_growth_gate.py's contract, including mapping_verified, daily_coverage_verified, activity_complete, contacts_complete and the live account ID. Eligible IDs are nonblank strings, contacts is a list, and a populated headcount names its source. Explicitly unresolved mappings may use null IDs and remain held; malformed value/container types are unusable input. Pipe session-only data to `python3 scripts/arr_growth_gate.py --packet -`; do not save raw financial output by default. The gate verifies coverage/arithmetic/date, routing, territory, recipient and suppression, and caps selected rows at max_accounts. Preserve every hold and shortfall; over-cap rows are held, never silently substituted after review.
7. Use each selected draft exactly: recipient is the adapter's billing email; subject/body are arr_growth.email_template; greeting uses the one contact's first name or the account-team fallback. Do not add or change wording, amounts, percentages, seats, discounts or ARR language. The template must already be reviewed; every instantiated recipient/subject/body still needs exact approval.
8. Show one Effect per selected account with account ID, headcount/source, contact ID or none and exact To/Subject/Body. Explain internal selection in the live conversation, where permitted, without persisting raw amounts. The adapter's reviewed retention contract must explicitly permit the recipient/draft and minimal selection receipt in the ignored run; otherwise stop before creating review artifacts.
9. After exact review, refresh live prerequisites and suppression, create one unsent draft per approved effect, then read each by returned draft ID and compare every field. A mismatch or uncertain result is reported, not repaired or retried blindly. New recipients/payloads need new review.
10. When the user reports a send, hand off that exact draft/send to signal-followup in arr_growth mode; it must obtain its own live sent proof and task approval.

## Outputs and readiness

The review shows data-through date, confirmed adapter success reference, query/selected counts and shortfall, one hold reason per excluded account, and exact draft effects. Persist only the fields authorized by the private retention contract, never raw per-user or billing-series rows. Session-only gate execution is not an auditable saved financial dataset; disclose that limit and retain a minimal adapter verification receipt/hash if authorized.

In inputs.json, list `drafts` as `{account_id, draft: "draft.json"}` entries and name the permitted `receipt` file. Each draft effect's `input` names that draft path. The receipt records `retention_authorized: true`, `success: true`, `reference`, `input_reference_kind: "immutable_snapshot"` and `immutable_input_reference`; the last identifies the actual immutable inputs, not merely a query execution ID. Stream the raw packet with the same immutable input reference to run preflight/review using `--arr-packet -`, as described in [workflows/run.md](../run.md). Raw input/output is not retained. Before creation, refresh the packet and compare its relevant selection prerequisites; without retained comparable evidence or still-available originals, prepare a fresh review and obtain approval rather than claiming the old inputs are unchanged.

02_result.json accounts for each approved draft with its provider and full readback reference. No result implies that mail was sent.

## Human check

Review adapter/date/coverage evidence, ownership, territory, suppression, fixed wording and every recipient. No unattended runs, sends, CRM tasks, contacts, account changes or financial data copied into CRM/knowledge files. Missing adapters remain an unavailable capability, even if synthetic tests pass.
