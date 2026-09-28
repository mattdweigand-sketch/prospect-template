---
workflow: signal-followup
reads: .local/config/policy.yaml, Gmail sent, Salesforce
writes: one Salesforce Task after approval
next: none, Salesforce holds the record
---

# signal-followup

One proven send becomes one open Salesforce Task (`policy.followup.max_tasks_per_run`). The completed Email Task is never created here, the existing mail-to-CRM sync owns it when configured. Manual only (`policy.approval.unattended_writes`).

Read this workflow's `CONTEXT.md` before the steps. Paths below are relative to the repo root. Use temporary sandbox files for checks; never store customer material in the checkout.

## Before starting

Read `setup/providers.md` for tool discovery, complete reads, pre-write revalidation and native readback, and `CONTEXT.md` for state and resume boundaries. Run `python3 scripts/preflight.py signal-followup`. Missing active configuration routes to `prospect-setup`; disabled optional modules stop. Verify that the tools required for the next step are actually available.

## Steps

1. Read `.local/config/policy.yaml` (`identity`, `approval`, `followup`). Never restate values.
2. Identify the send. the seller names a recipient, a subject, or a Gmail draft from this thread. Run a live Gmail `from:<policy.identity.owner_email> in:sent to:<email>` search and keep hits whose subject and date match. Record message id, thread id, subject, aware sent timestamp, recipient. A draft, a thread summary, or memory is never proof.
3. Resolve in Salesforce. Account by the recipient's domain (Id, OwnerId). Contacts on that Account where `Email = '<recipient>'` (Id, Email). Tasks on those Contacts, any status (Id, Subject, Status, Description). Read only.
4. Build the packet in the shape from the gate docstring. `signal.signal_type` and `signal.angle` come from the outreach gate's allow verdict shown in this thread. `angle` is the chosen messaging angle. Preserve the historical label; do not look it up in today's talk track. A legacy `unit` from an existing sent message is accepted without conversion. Both are `arr_growth` for an ARR growth send. Absent in the thread, ask the seller, never guess. Run `python3 workflows/signal-followup/followup_gate.py --packet <p.json>`. Add `--mode arr_growth` only when this thread shows the send came from `signal-arr-growth`. Any `block` ends the run. Report the reasons. Do not work around them.
5. Report in the format below with the gate's `task` object as Proposal 1. Stop and wait. Approval covers those exact fields. Any change to a field, the recipient, or the sent message is a new proposal.
6. After approval create one Task with exactly those fields. SOQL the returned Id with every approved field (`policy.approval.readback_required`). Run `python3 _shared/scripts/readback_check.py --expected <approved-task.json> --actual <returned-record.json>` on the exact gate Task and returned record. A missing field or mismatch stops; report it without repairing or repeating the write.

## Report

```
Send: <recipient> | "<subject>" | <sent_at in identity.timezone> | message <id>
Salesforce: Account <Id> owner the seller | Contact <Id> | existing Tasks on Contact: <n>
Sync Task: <Id or not yet landed>   (advisory, never blocks)
Gate: allow | mode <standard|arr_growth>

Proposal 1. Salesforce Task
  Subject, WhatId, WhoId, OwnerId, Status, Priority, TaskSubtype, ActivityDate, Description as emitted by the gate

After approval:
Created: <Task Id> | readback: match / mismatch on <fields>
```

## Refuse

- Creating a Contact or an Event. The one Task is the only write.
- Sending or drafting email. That is `signal-outreach`.
