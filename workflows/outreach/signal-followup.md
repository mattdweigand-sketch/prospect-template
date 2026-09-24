# Follow-up task after a proven send

Manual only. One uniquely proven sent email may produce one open CRM task.

## Load / Skip

- Working: output/{run-id}/request.md, a named sent email and the exact outreach/ARR handoff with signal and claim IDs.
- Reference: workflows/run.md, _shared/rules.md; policy.json identity and followup_signal; taxonomy/claim IDs only for standard mode; adapters.md sent-mail proof, CRM resolution/task mappings, sync ownership.
- Skip: drafting, new signal research, enrichment, warehouse data, knowledge sources and unrelated sends.

## Process

1. Identify the requested recipient, subject or prior draft. Search **live sent mail** in this run for the recipient and match subject/date. Record message ID, thread ID, exact subject, timezone-aware sent timestamp and recipient with the provider lookup reference. A draft, queued send, summary or memory is not proof. Zero hits or multiple plausible hits stops; do not guess which was sent.
2. Resolve one CRM account from the recipient domain, with owner and open opportunities; require the configured owner and no open deal. Read all contacts on that account with matching email and all tasks on the matching contact, every status. Record complete pagination/coverage. Exactly one matching contact belonging to the account is required; comparison is case-insensitive.
3. Copy signal_type and claim_id from the reviewed outreach gate handoff. Standard mode requires known tier 1/2 and claim IDs. Use arr_growth mode only for a proven ARR-growth handoff, with both IDs set to arr_growth. Missing attribution requires user clarification, never invention.
4. Build sent, sent_lookup_reference, account, contacts, contacts_complete, tasks, tasks_complete and signal in the packet. Run `python3 scripts/followup_gate.py --packet output/RUN_ID/followup.json` (or `--mode arr_growth`). The gate blocks duplicate subject/message ID and any open task with the configured follow-up prefix. Closed-status exceptions apply only to that prefix test, not an exact duplicate.
5. Due date uses the sent date in identity.timezone plus followup_signal.due_calendar_days for standard mode, or growth_due_business_days weekdays for ARR mode. Weekdays exclude weekends, not local holidays. Naive timestamps and a due date before today block; a due date today is allowed. Do not shift an expired date to work around the gate.
6. On allow, map the normalized task to the reviewed native provider fields **before** approval. Show subject, account/contact/owner IDs, status, priority, subtype, due date and description including message/thread/signal/claim IDs. Do not add an extra Type field or provider default without including it in the proposal. The configured mail sync owns completed Email activity; its absence is advisory and never permission to duplicate it.
7. After exact review under workflows/run.md, repeat the sent proof and duplicate/ownership/open-deal reads. A changed message, field or preimage needs revised review. Create one open task with precisely the approved native fields. Read back the returned ID and compare all fields; report mismatches without repair or replay.

## Outputs and readiness

01_review.md shows sent proof, local sent time, CRM identity, contact/task coverage, any sync-task status, gate verdict/mode and the exact Effect. Declare the packet, proof references and gate result as artifacts. A block ends the run with reasons and no effect; it is not a prompt to try a looser match.

02_result.json accounts for the one approved task and its provider/readback references. A second send requires a separate run.

## Human check

Review send identity, duplicates, due date, attribution and exact native task fields. No completed Email tasks, contacts, events, opportunities, drafts or sends are created here. Approval of the earlier draft did not authorize this task.
