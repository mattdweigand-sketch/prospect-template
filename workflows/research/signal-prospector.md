---
type: workflow
command: signal-prospector
mode: write
---
# signal-prospector

Discover candidate accounts, resolve CRM ownership, and propose exact account claims.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md; load _shared/icp.md, _shared/taxonomy.json and _shared/claims.json only where a step names them.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, web; contact enrichment optional.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Load the approved _shared/icp.md, taxonomy and configured territory limits. Find at most policy.prospector.max_candidates candidates from public signals. An optional adoption source must use the aggregate privacy contract of signal-user-scan.
2. For each candidate, use the signal-scan qualification process and obtain dated headcount or other territory evidence. Apply the configured admission rule and disqualifiers. Unknown qualification data produces a hold, not a guessed fit.
3. Resolve domain matches, owner activity and open Opportunities in live CRM. Route new, transferable, already-owned, active-deal and owned-elsewhere candidates by policy.routing. Existing CRM state is the deduplication source; do not build a parallel account ledger.
4. Find a professional contact only when needed for a proposed claim. Use existing CRM records or verified enrichment; do not construct email addresses from patterns.
5. Propose Account creation or explicitly permitted owner transfer and any Contact creation as distinct numbered effects with exact fields and source evidence. An uncertain contact can leave an Account-only proposal.
6. After approval, repeat the domain and owner checks before applying. A new match or changed owner invalidates the affected proposal. Verify each created or transferred record. This workflow does not create Opportunities or draft outreach.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Check admission evidence, territory, ownership and exact claim fields for each candidate. Approve only the listed effects; discovery never grants ownership.
