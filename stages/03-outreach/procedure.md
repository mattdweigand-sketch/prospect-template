---
workflow: signal-outreach
reads: .local/config/policy.yaml, .local/config/talk-track.md, relevant ICP persona section, bundle in thread, email provider sent, CRM Tasks
writes: one email draft after approval
next: signal-followup after the seller sends
---

# signal-outreach

Turns one qualified bundle into one email draft (`policy.outreach.max_drafts_per_run`). The bundle arrives as fenced JSON in the thread from a scan skill. This skill never finds signals, never sends, and never writes to CRM. Product wording comes only from `policy.outreach.talk_track.file`.

Read this workflow's `CONTEXT.md` and its scoped inputs before the steps. Run its Audit before presenting the report or proposal, and its completion checks after any approved write. Honor its conditional checkpoints. Paths below are relative to the repo root. Use temporary sandbox files for checks; never store customer material in the checkout.

## Before starting

Read `shared/providers.md` for tool discovery, complete reads, pre-write revalidation and native readback, and `CONTEXT.md` for state and resume boundaries. Run `python3 _system/scripts/preflight.py signal-outreach`. Missing active configuration routes to `prospect-setup`; disabled optional modules stop. Verify that the tools required for the next step are actually available.

## Steps

1. Read `.local/config/policy.yaml` (`outreach`, `approval`, `identity`, `user_scan`), `policy.outreach.talk_track.file` (relative to `.local/config/`), and the relevant Target personas section of `.local/config/icp.md`. Never restate their values in the report.
2. Intake. Take the bundle from the thread. A web bundle must carry `gate`, `quote`, `source_url`, `published_date`, `date_basis`, `checked_at`, `account_domain`, `classification: active_initiative`, and `relevance: relevant_to_offer`, and an evidence-to-offer `fit_reason`. Old bundles missing those fields need a new scan; do not invent them to pass a gate. No bundle, no draft. Do not reconstruct one from memory or a summary. Re-fetch the source page when `checked_at` is older than `policy.outreach.bundle_checked_max_age_hours`. An adoption sentence needs a privacy-checked `signal-user-scan` bundle from this thread and repeats only its `policy.user_scan.statements` entry. Without one, leave the sentence out. For a `paid_individuals_present` draft, wrap that bundle and use the wrapper as the bundle.
   ```
   {signal_type: paid_individuals_present, published_date: <data_through_date>, checked_at: <now, ISO with offset>,
    quote: <policy.user_scan.statements[adoption]>, date_basis: warehouse, account_domain: <account_domain>,
    account_name: <account_name>, adoption_bundle: <the privacy-checked bundle>}
   ```
3. Recipient. Prefer the person named in the signal. Sources in `policy.outreach.recipient_sources` order. Query CRM Contacts on the Account with Email and Id; a CRM recipient needs its Contact Id. Search email provider for prior threads with the person, then the configured verified-contact enrichment provider. If the seller explicitly supplies the address here, record `User supplied in this conversation`; never guess an address or relabel its source.
4. Activity. Re-read the Account owner and open deals and populate the packet's `account` object from the native results. It must be owned by the configured seller with no open deal. Read CRM Tasks and Events on the Account and Contact inside `policy.outreach.activity_lookback_days`, including date, target, and each Task's status and subtype. Search the configured email provider for native sent messages to that address in the same inclusive window. All task, event and sent-message rows go into `activity` unfiltered, with a separate `reads` receipt for each service read as defined by the gate. Complete all pages; mark truncated results incomplete. Classify Task statuses through `policy.outreach.task_status_map`; unknown statuses stop. Missing or failed reads stop; they are not empty results. Use `who_kind: contact_id | email` for known targets and preserve unknown targets as null so the gate can suppress conservatively.
5. Choose one messaging angle from `.local/config/talk-track.md` for the verified initiative and recipient's evidenced responsibility. State the persona/responsibility in ordinary language and give one sentence explaining the connection. Titles are search aids, not proof of ownership or authority. Do not translate the persona into a legacy ID or select a numbered answer. If responsibility is unknown, research it or ask the seller; do not fabricate a rationale.
6. Draft. Follow `policy.outreach.draft_shape`: one verified observation, one relevant connection to the configured offer, one easy question. Use the Core messaging and Match the angle sections selectively; preserve the document's Claim boundaries. Consult its supporting evidence only for claims actually used. Do not infer pain, budget, tool dissatisfaction, or buying authority. Keep benchmark statistics, customer names, and unsupported numerical claims out of the first message. Review source meaning, recipient fit, claim support and limitations before proposing. The packet's `talk_track` is `{angle, persona, pick_reason}` in ordinary language; it records judgment, not proof that judgment is correct. Run `python3 _system/scripts/lint_draft.py --body <body.txt>` for the advisory style review in `policy.outreach.lint`, using the reviewed voice sample from `policy.email_voice.file`. Style warnings do not determine claim support or approval.
7. Gate. Write the packet (shape in the script docstring) and run `python3 _system/scripts/outreach_gate.py --packet <p.json>`. Exit 1 means fix the named reason or stop. Never edit the packet to pass. `flags` never block. Copy them into the report.
8. Propose. Set `cc: []` and `bcc: []`, map the canonical draft through `provider_map.py --record email.draft.write`, and show the exact native payload. Show exact To, Subject, Body, recipient source and title, signal type, verified responsibility, chosen angle, rationale, and the gate verdict. Number it. Stop and wait.
9. On approval create the one email draft. Retain both returned draft and message identifiers. Read the full native message using the identifier required by the configured tool (`policy.approval.readback_required`). Follow `shared/providers.md` for MIME and readback handling. Compare the complete returned `to`, `subject`, and `body` with the exact approved values using `python3 _system/scripts/readback_check.py --email --expected <approved.json> --actual <readback.json>`. Normalize with `email.draft.read`, including complete CC/BCC fields explicitly; missing or added recipients fail. Use returned field values, never reconstruct them from the proposal. Missing full readback or a mismatch stops; report it without repairing or repeating the write.
10. Hand off. Say that `signal-followup` runs after the seller sends. Do not create a Task here.

## Report

```
Bundle: <account> | <signal_type> | <published_date or observed current> | source checked <checked_at date>
Recipient: <name>, <title> | <email> | source: <policy source>
Activity: <n> CRM rows, <n> email provider sent, last touch <date or none>
Responsibility: <verified role> | Angle: <plain-language messaging angle>
Pick reason: <one sentence>
Gate: allow / block (<reasons>) | flags: <gate flags or none>

Proposal 1. email draft
To: <email>
Subject: <subject>
<body>

Limits: <material inference, uncertainty, or unresolved style issue; omit when none>
```

## Refuse

- Sending email, replying, or forwarding. Ever (`policy.approval.never`).
- A recipient address that is guessed, pattern-built, or from a source not in policy.
- Unsupported product claims or wording that exceeds the talk track's Claim boundaries. An angle label or passing gate does not establish claim support.
- Any CRM write. Follow-up Tasks belong to `signal-followup`.
- Ledgers or files written to the project. email provider is the record of what was drafted.
