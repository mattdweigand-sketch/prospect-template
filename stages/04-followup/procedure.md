---
workflow: signal-followup
reads: .local/config/policy.yaml, email provider sent, CRM
writes: one CRM Task after approval
next: none, CRM holds the record
---

# signal-followup

One proven send becomes one open CRM Task (`policy.followup.max_tasks_per_run`). The completed Email Task is never created here, the existing mail-to-CRM sync owns it when configured. Manual only (`policy.approval.unattended_writes`).

Read this workflow's `CONTEXT.md` before the steps. Paths below are relative to the repo root. Use temporary sandbox files for checks; never store customer material in the checkout.

## Before starting

Read `shared/providers.md` for tool discovery, complete reads, pre-write revalidation and native readback, and `CONTEXT.md` for state and resume boundaries. Run `python3 _system/scripts/preflight.py signal-followup`. Missing active configuration routes to `prospect-setup`; disabled optional modules stop. Verify that the tools required for the next step are actually available.

## Steps

1. Read `.local/config/policy.yaml` (`identity`, `approval`, `followup`). Never restate values.
2. Identify the send. The seller names a recipient, subject, or draft from this chat. Use `email.search` with the configured seller, recipient and date scope, then `email.read_message` for complete matching native messages. Record `message_id`, `is_sent: true` only from native sent-state evidence, subject, aware `sent_at`, and `to`. Keep `thread_id` when available; it is optional. A draft, summary or memory is never proof.
3. Resolve in the configured CRM: account by recipient domain, its owner, contacts on that account with the recipient's exact address, and every task on those contacts regardless of status. Normalize records through the reviewed mappings. Read all pages; missing or failed reads stop.
4. Build the packet in the shape from the gate docstring. `signal.signal_type` and `signal.angle` come from the outreach gate's allow verdict shown in this thread. `angle` is the chosen messaging angle. Preserve the historical label; do not look it up in today's talk track. A legacy `unit` from an existing sent message is accepted without conversion. Both are `arr_growth` for an ARR growth send. Absent in the thread, ask the seller, never guess. Run `python3 _system/scripts/followup_gate.py --packet <p.json>`. Add `--mode arr_growth` only when this thread shows the send came from `signal-arr-growth`. Any `block` ends the run. Report the reasons. Do not work around them.
5. Report in the format below with the gate's `task` object as Proposal 1. Stop and wait. Approval covers those exact fields. Any change to a field, the recipient, or the sent message is a new proposal.
6. Before approval, render the gate task through `provider_map.py --record crm.task.write` and show the exact native payload and associations beside the canonical proposal. After exact approval and fresh revalidation, create one task. Read the resulting native record by its returned ID (`policy.approval.readback_required`), normalize with `crm.task.read`, and run `readback_check.py --expected <approved-task.json> --actual <normalized-readback.json>`. Follow `shared/providers.md` for extra native-field comparisons. Missing fields or mismatches stop; report without repairing or repeating the write.

## Report

```
Send: <recipient> | "<subject>" | <sent_at in identity.timezone> | message <id>
CRM: Account <Id> owner the seller | Contact <Id> | existing Tasks on Contact: <n>
Sync Task: <Id or not yet landed>   (advisory, never blocks)
Gate: allow | mode <standard|arr_growth>

Proposal 1. CRM Task
  subject, account_id, contact_id, owner_id, status, priority, subtype, due_date, description as emitted by the gate; exact mapped native payload

After approval:
Created: <Task Id> | readback: match / mismatch on <fields>
```

## Refuse

- Creating a Contact or an Event. The one Task is the only write.
- Sending or drafting email. That is `signal-outreach`.
