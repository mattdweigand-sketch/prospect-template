---
type: workflow
command: signal-user-scan
mode: read
---
# signal-user-scan

Produce an organization-level adoption finding using a configured private-data adapter.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md; load _shared/icp.md, _shared/taxonomy.json and _shared/claims.json only where a step names them.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, adoption.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Confirm the Account belongs to the configured owner and has no open Opportunity. Resolve a single domain and account ID.
2. Require the adoption adapter and its permitted fields in _shared/adapters.md. Without it, report unavailable; never substitute inferred usage from public interest or employee profiles.
3. Read aggregate organization-level adoption categories through the configured data-through date. Exclude user names, email addresses, seat counts, query content and individual activity timing from the handoff bundle.
4. Write output/{run-id}/adoption.json containing only account_name, account_id, account_domain, data_through_date, adoption and source_reference. Adoption must be org_adopted, individuals_only, none_found or unknown. Unknown and none_found support no adoption claim.
5. Verify every field against the configured source and permissions. In the review, distinguish the source's data date from the time checked, and give only the approved aggregate statement for the observed category.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested read-only deliverable, source coverage, evidence and unresolved items.
- Declare adoption.json in the review's artifacts list when a bundle is produced; unavailable adapter findings produce no bundle.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Its effects list is empty.

## Human check
Verify the account, data date, permissions and exact aggregate statement. The bundle must not expose individual activity or imply absent evidence proves non-use.
