# Propose fixed-template drafts for self-serve ARR growth

## Inputs

| Kind | Path or source | Load / purpose |
|---|---|---|
| Reference | `../../.local/config/policy.yaml` | identity, approval, salesforce, arr_growth, warehouse, prospector.headcount_sources, outreach.suppressing_task_subtypes |
| Machine settings | `../../.local/config/icp.md` | Territory metadata read by the gate; the agent need not load the body |
| Tool | `arr_growth_source.sql`; `arr_growth_gate.py` | Read-only source query, eligibility checks and exact template draft |
| Tool | `../../_shared/scripts/route_candidate.py`; `../../_shared/scripts/readback_check.py` | Ownership routing and approved-field readback |
| Working | warehouse rows; completed Salesforce and Gmail reads | Current account, contact, territory and suppression evidence |

## Process

Follow `procedure.md`: read growth candidates, validate routing and suppression, then propose each fixed-template draft. This is an independent workflow; it does not run the public scan or messaging workflow.

## Output

Numbered draft proposals in the thread; approved Gmail drafts with exact readback. The template lives in policy, so talk-track content is not an input. Nothing is written to this folder.

## Human check

Approve each exact recipient, subject and body separately. Changed fields require a new proposal. the seller sends manually.

## Next

`../signal-followup/` in arr_growth mode after a proven send.
