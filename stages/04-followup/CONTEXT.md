# Log one proven send as an open CRM Task

## Inputs

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Procedure | `procedure.md` | Full file | Detailed steps, report and stop conditions |
| Reference | `../../shared/providers.md` | Full file | Tool discovery, complete reads, mappings and write/readback rules |
| Settings | `../../.local/config/policy.yaml` | identity, approval, followup | Installed values and boundaries |
| Tool | `../../_system/scripts/followup_gate.py`; `../../_system/scripts/readback_check.py` | CLI and packet docstrings as used | Task validation and approved-field readback |
| Working | Native sent message, CRM Account/Contact/Task reads and same-thread outreach verdict | Complete reads and historical signal/angle labels | Prove the send and prevent duplicate or misassociated Tasks |

## Process

Step numbers match `procedure.md`; it owns the detailed rules.

1. Read scoped settings.
2. Prove the send with a complete native message.
3. Resolve ownership, exact recipient Contact and all Tasks across statuses and pages.
4. Build the packet from the historical outreach verdict and run the follow-up gate.
5. Map the Task to native fields, run the Audit, present Proposal 1 and stop for approval.
6. After exact approval and fresh revalidation, create one Task and verify complete native readback.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 5 | Exact canonical Task, mapped native fields, associations and sent-message identity | Approve exact fields; a changed field, recipient or sent message requires a new proposal |

## Audit

| Check | Pass Condition |
|---|---|
| Send proof | Native sent state and complete message fields identify the actual send. |
| Association and duplicates | The recipient, Account, Contact and complete Task reads support the gate result. |
| History | Signal and angle come from this send’s verdict; ARR mode has demonstrated origin. |
| Completion | The one created Task matches all approved fields after normalization and native comparison. |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Task proposal | Current chat | Procedure’s Proposal 1 with exact canonical/native fields |
| Approved Task | Native CRM | Task ID and complete readback result |

## Next

None. CRM holds the record; this workflow does not create Contacts, Events or email.
