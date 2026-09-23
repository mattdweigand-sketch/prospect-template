---
type: workflow
command: signal-followup
mode: write
---
# signal-followup

Create one CRM follow-up task after a uniquely identified email was actually sent.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md; load _shared/icp.md, _shared/taxonomy.json and _shared/claims.json only where a step names them.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: crm, mail.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Read sent mail in this run and identify exactly one message using the user-supplied thread, recipient, subject and date. A saved draft, local run record or remembered send is not proof. Resolve ambiguity before proposing anything.
2. Resolve one Contact matching the recipient on the correct owned Account. Check Account routing and existing Tasks by message ID, matching subject and open follow-up prefix.
3. If a duplicate or existing open follow-up exists, report it. Otherwise calculate the due date from the actual send date in policy.identity.timezone and the configured cadence. A date already in the past requires user direction.
4. Propose the exact Task subject, date, status, priority, owner, Contact and Account links. Include the provider message/thread references and signal/claim IDs when known. Do not fabricate IDs for an unrelated manual email.
5. After approval, refresh the duplicate check, create the one Task and read it back. Do not create a completed email activity if provider synchronization owns it. Do not draft or send a new email.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Verify the unique sent-message evidence, matching Contact, no duplicate, and exact Task fields. Approve only that follow-up Task.
