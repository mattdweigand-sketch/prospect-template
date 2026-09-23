---
type: workflow
command: signal-arr-growth
mode: write
---
# signal-arr-growth

Find eligible self-service growth accounts through a configured billing adapter and propose template drafts.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md; load _shared/icp.md, _shared/taxonomy.json and _shared/claims.json only where a step names them.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, mail, billing.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Require a configured billing/ARR adapter with metric definitions, daily coverage requirements and permitted recipient source. Without it, report unavailable. Never copy the original deployment's private SQL or assume its schema.
2. Read the configured trailing window and require complete comparable snapshots. Do not zero-fill missing dates. Resolve organization-to-account mapping and rank positive net changes using the configured metric definition.
3. Check live Account ownership, no open Opportunity, territory, contact permissions, subscription platform and account-wide activity suppression. Replica ownership alone is insufficient. Uncertain mapping or contact permissions holds the account.
4. For at most policy.arr_growth.max_accounts, propose the exact approved template from policy.arr_growth.email_template. Never infer a person's name from an email address. Keep internal revenue figures, billing provenance and organization identifiers out of the draft.
5. Obtain separate approval for each draft, re-check suppression, create it unsent and read it back. No sending or CRM changes belong here. After a proven send, signal-followup can propose its separately approved Task using the configured growth cadence.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Check full data coverage, account and recipient eligibility, suppression and exact template wording. Internal growth data supports selection, not customer-facing assertions.
