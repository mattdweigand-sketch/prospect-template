# Run contract

One run is one task-scoped review and, where applicable, its approved effects.
This is a two-stage pipeline inside each workflow. The numbered output files
encode that order; the sibling workflow families themselves have no execution order.

## Inputs and start

- Working: the user's request and its supplied run ID; exact source paths or provider references recorded in output/{run-id}/request.md.
- Reference: the selected workflow, its family CONTEXT.md, _shared/rules.md and only the policy sections and adapter entries it names.
- Copy _templates/run/ through `python3 scripts/runs.py init RUN_ID COMMAND`.
- Do not reuse a run ID or load prior runs, unrelated workflows, all customer records or all factory material. A handoff names the exact source run and its reviewed output; presence of another run never selects it.

## 01 — prepare the review

Work within the request and write output/{run-id}/01_review.md. It contains
source coverage, attributed facts, unresolved gaps, the requested deliverable,
and exact proposed effects where relevant. Number effects with headings such
as `## Effect A1`; keep their full fields or draft text under that heading.
Read-only deliverables have no effect headings. Fill inputs.json with the selected
workflow's named inputs and explicit coverage gaps. Its effects map must bind
every Effect heading, for example `"A1": {"kind": "draft", "input": "packet.json"}`.
Paths are run-relative regular files; manifests contain no executable commands.
Account/contact creation, owner transfer, draft, task and configuration effects
are allowed only in their owning workflow. A new-account contact also names its
account_effect; other effect graphs are unsupported.

Keep extra human review materials in the artifacts frontmatter JSON list,
for example `artifacts: ["voice.txt"]`. Machine inputs are included in the snapshot
automatically. Missing files prevent review; edits invalidate recorded hashes.
After preparing the deliverable, set `status: ready` and run:

`python3 scripts/runs.py preflight RUN_ID`

Preflight replays the complete gates and compares saved results. A saved allow
flag is insufficient. Include its issues in the review. Explicit gaps permit a
limited finding; every proposed effect still needs passing prerequisites, even
if the user will approve only a subset. Handoff eligibility belongs to the
selected artifact, never to the report merely because it was reviewed.

Human checkpoint: show the review to the user and allow edits. Do not proceed
to stage 02 until they have read it. Record the real conversation reference,
reviewer and exactly approved effect IDs in output/{run-id}/review.json using:

`python3 scripts/runs.py record-review RUN_ID --reviewer NAME --approval-ref REFERENCE --effects A1`

Omit --effects for a reviewed read-only deliverable. This command records an
existing approval; running it is never a way to obtain one. The snapshot covers
the review, manifest, checked files, selected contracts/helpers and the factory
files declared by the route registry. The compact validation record stays in
review.json. The same preflight runs during record-review. Setup/refresh require
`--source SOURCE_CLONE`; ARR requires `--arr-packet -`. `--now` is for deterministic
synthetic replay; live work uses the current time. Preflight returns 0 when
reviewable, 1 for unmet prerequisites and 2 for unusable input.

## Named handoffs

The downstream manifest's handoff object names run_id, workflow,
approval_reference, review (a retained copy of upstream review.json), selected
(the upstream artifact path), and artifacts (a map from upstream paths to local
copies). Retain only the selected export and its required artifacts. Preflight
checks the review contract, named selection and hashes. If the exact upstream
run exists locally, its review must still be current; otherwise use the explicit
portable export. Never search unrelated runs or fabricate missing receipts.
Exports preserve the checked account ID. Follow-up's account and contact
association must match that frozen target, including across a portable handoff.

Outreach preserves the original reviewed source artifacts. A refreshed source
has a separate receipt/page/result and actual fetch time; changed page bytes
alone do not invalidate provenance, but changed signal facts require a revised
research review. Follow-up checks frozen approved draft attribution and current
sent/CRM evidence, without reapplying the earlier drafting freshness window.

ARR raw packets enter preflight and record-review only through stdin. Retain
only authorized draft/selection receipts; raw rows, amounts and their hashes
must not enter saved files or preflight output. The receipt identifies an
authorized immutable input snapshot, not merely a query execution. Financial
validation is marked transient and cannot be replayed from the retained files.
Before creation, stream current input again and compare original financial
preimages in memory or through that immutable snapshot. After session loss,
missing original inputs require a fresh review; matching draft text alone is
insufficient. Provider truth and consent still require the cited human evidence.

## Reviewed local configuration changes

For a workflow such as signal-refresh that changes factory inputs, the exact
review includes the proposed complete file content or diff. Stage its new bytes
inside the run and compute SHA-256. Add one frontmatter line after status:
`expected_after: {"A1": {"_shared/claims.json": "64-character SHA-256"}}`.
The real value is the staged file hash, not the explanatory placeholder above.
Only named shared inputs already in the review snapshot may be changed this way.
All changed companion files must be included in one coherent configuration
effect. Preflight validates the full proposed factory and exact postimage hashes.
The recorded approved IDs select which postimages are authorized. Changing a
file to any other revision invalidates review. A landed postimage without a
result is recovery_required: inspect what happened; never replay the write.

## 02 — apply and report

First run `python3 scripts/runs.py status RUN_ID` and current preflight with its
required source or transient input. Continue only with a current review and
actual user authorization. Use the selected workflow and shared rules for each
approved effect. Re-read live preimages and stop the affected
effect if they changed. Apply through the configured host tools, then read back.

Write output/{run-id}/02_result.json with recorded_at, summary, review_snapshot
(the exact snapshot from review.json), and one effects entry per approved ID.
Each entry has id, status (verified, pending, failed, skipped), provider_reference,
readback_reference and detail. Failed, skipped and pending effects remain
unresolved; the report explains why. A read-only result has an empty effects list.

Human checkpoint: inspect the result and cited provider evidence. Review files
remain local. Do not copy them into the reusable repository or claim public
release checks make customer data suitable for publication.

## Resume and status

Inspect only this run's declared request, review, review record and result.
`runs.py status` reports draft, awaiting_human_review, review_stale,
review_current, recovery_required, result_stale, incomplete or completion_recorded. The last means
the required local record shape is complete, not independently proven service
success. A template, stale result or unreviewed file never completes the run.
Status checks frozen validation and hashes; elapsed time alone does not erase
historical completion. A new effect attempt uses current preflight. Older reviews
without the checked-input contract remain historical records but need prepared
inputs and a fresh review before another effect or actionable handoff.
