---
type: workflow
command: signal-outreach
mode: write
---
# signal-outreach

Prepare one evidence-backed cold email and create an unsent draft after exact approval.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md; load _shared/icp.md, _shared/taxonomy.json and _shared/claims.json only where a step names them.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, mail; contact enrichment optional.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Accept an explicitly identified qualified bundle from the current task or a user-selected prior run. Re-open its source if older than policy.outreach.bundle_max_age_hours. Carry the actual source timestamp; do not refresh the timestamp without re-fetching. Re-check CRM ownership and open-deal routing.
2. Resolve the recipient from configured verified sources, never a guessed address. Read CRM Tasks and Events and sent mail for the Account and Contact. Record all relevant activity and apply configured suppression. An unavailable required source prevents a ready draft.
3. Select one approved claim from _shared/claims.json. Match the signal's creates_work and the recipient's responsibility, then inspect signal binding, vertical and persona. Report the pick, runner-up and rationale. Apply policy.outreach.fit_mode; warn mode must disclose every mismatch and label best_guess. A missing or unapproved claim always stops the draft.
4. Build the product paragraph from claim within limit and phrase it for kind: reported example, capability, inference or evaluation advice. Sample track wording is optional. Internal evidence stays out of the email. A customer name requires that chosen row's external_ok permission.
5. Write the event fact, likely work for this recipient, bounded claim and one question. Show exact To, Subject and Body, recipient provenance, suppression results, source freshness, selected claim ID, fit warnings and thin spots in 01_review.md. An adoption sentence additionally needs a current reviewed adoption bundle.
6. Verify every number and proof name against the chosen claim or source. Review meaning as well as literal matches; no hash or code gate proves the sentence is true. Create only the approved unsent draft, read it back, and hand off to signal-followup only after the user actually sends.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Read the exact recipient, subject and body alongside claim, limit, kind and source. Explicitly inspect any best_guess warning. Approve this one draft by effect ID.
