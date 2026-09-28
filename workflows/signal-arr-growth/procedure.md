---
workflow: signal-arr-growth
reads: .local/config/policy.yaml, Snowflake, Salesforce, Gmail sent
writes: Gmail drafts from the fixed template, one approval each
next: signal-followup, mode arr_growth, after the seller sends
---

# signal-arr-growth

Growing self-serve spend is the signal. The billing contact is the recipient. The email is a fixed template that names no figures. Manual only (`policy.approval.unattended_writes`). Each draft is its own approval.

Read this workflow's `CONTEXT.md` before the steps. Paths below are relative to the repo root. Use temporary sandbox files for checks; never store customer material in the checkout.

## Before starting

Read `setup/providers.md` for tool discovery, complete reads, pre-write revalidation and native readback, and `CONTEXT.md` for state and resume boundaries. Run `python3 scripts/preflight.py signal-arr-growth`. Missing active configuration routes to `prospect-setup`; disabled optional modules stop. Verify that the tools required for the next step are actually available.

## Steps

1. Read `.local/config/policy.yaml` (`identity`, `approval`, `salesforce`, `arr_growth`, `warehouse`, `prospector.headcount_sources`, `outreach.suppressing_task_subtypes`). Never restate values.
2. Run the hash-verified private SQL copy named by `policy.warehouse.queries.arr_growth_source.path` through the configured warehouse tools, read-only, async, warehouse `policy.warehouse.name`. Bind `policy.warehouse.data_date`, `policy.arr_growth.window_days`, `policy.identity.sfdc_user_id`, and `policy.arr_growth.candidate_rows` in header order. Fetch rows only after status is success. Zero rows is a finding. Report it and stop.
3. Read Salesforce in batches with `IN` lists. Accounts by `salesforce_account_id` (Id, Name, OwnerId, Owner.IsActive, NumberOfEmployees, Website) and open Opportunities per `policy.salesforce.open_opportunity`. Record completed reads in the packet's `reads` map. Missing owner or Opportunity facts stop routing. Only rows that route `scan` per `_shared/scripts/route_candidate.py` proceed.
4. Headcount. Use NumberOfEmployees when set and record `headcount_source: Account.NumberOfEmployees`. Otherwise look for the first dated hit in `policy.prospector.headcount_sources`; mark `reads.headcount_lookup` true only after that lookup completes. Unknown stays null and holds the row.
5. For each row still eligible, read Contacts on the Account whose Email matches `billing_email` (Id, Email, FirstName). Save Account Id and Website as `{"accounts": [{"id": "<Id>", "website": "<Website>"}]}` and run `python3 workflows/signal-arr-growth/arr_growth_gate.py --queries <accounts.json>`. Execute its Task, Event, and Gmail queries unchanged. The helper uses AccountId, `policy.outreach.suppressing_task_subtypes`, the Account Website domain, and the inclusive `policy.arr_growth.suppression_days` boundary. An unusable Website holds the row. Record the latest returned touch as `last_touch_date`, or null only after all reads completed with no touch. Set `reads.contacts`, `reads.tasks`, `reads.events`, and `reads.gmail_sent` only for completed native reads, including successful empty results. Failed or skipped reads stay false.
6. Build the packet in the shape from the gate docstring, including Account Website and the completed-read flags. Use a temporary sandbox packet, never the checkout or a published artifact, and run `python3 workflows/signal-arr-growth/arr_growth_gate.py --packet <p.json>`. The gate validates the data date, daily coverage, arithmetic, routing, read coverage, and suppression, and selects at most one row per Account. `block` means nothing to draft; exit 2 means unusable input. On block or exit 2, report the holds or error and stop. An allow result may also contain held rows; report them beside the selected proposals. Remove temporary customer-data packets after the run.
7. Report in the format below. Each selected account is one numbered proposal with the gate's exact `draft`. Stop and wait. Approval covers that recipient, subject, and body. Any change is a new proposal.
8. After approval create one Gmail draft per approved proposal with exactly those fields, then retain both returned draft and message identifiers and read the complete native message with the identifier required by the configured tool (`policy.approval.readback_required`). Gmail `read_email` takes the message id. Follow `setup/providers.md` for MIME and readback handling. Run `python3 _shared/scripts/readback_check.py --gmail --expected <approved-draft.json> --actual <native-readback.json>` against the complete `to`, `subject`, and `body`. Preserve any returned CC/BCC fields; the checker rejects added recipients. Extract fields only from the native return; never reconstruct readback from the proposal. A mismatch stops the run and is reported, not repaired or retried automatically.
9. When the seller reports a send, hand to `signal-followup` with mode `policy.arr_growth.followup_mode`.

## Report

```
Data through: <date> | Query rows: <n> | Selected: <n> of <max> | Shortfall: <n>

Held: <account or org name> | <hold>            (one line each. Figures stay inside policy.arr_growth.internal_only)

Proposal 1. Gmail draft
  Account: <name> | <Id> | headcount <n> (<source>) | Contact: <Id or none>
  ARR: <baseline> to <current>, net +<n> over <window> days   (internal, policy.arr_growth.internal_only)
  To: <billing_email>
  Subject: <subject>
  <body verbatim>

After approval:
Draft <id> created | readback: match / mismatch on <fields>
```

## Refuse

- Reading anything in Snowflake beyond the reviewed private query corresponding to `workflows/signal-arr-growth/arr_growth_source.sql`, or any field in `policy.warehouse.forbidden`.
- Sending email, creating Tasks, Contacts, or Accounts. Claims go to `signal-prospector`. Tasks go to `signal-followup`.
