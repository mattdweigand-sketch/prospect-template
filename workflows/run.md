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
Read-only deliverables have no effect headings. List every accompanying source,
bundle or deliverable file in an artifacts frontmatter JSON list, using run-relative
paths such as artifacts: ["bundle.json", "source.txt"]. Missing declared files
prevent review recording; changing their bytes invalidates the recorded review. The chosen workflow defines
its content checks and human review. Only after those checks pass, change
the artifact's frontmatter from `status: draft` to `status: ready`.

Human checkpoint: show the review to the user and allow edits. Do not proceed
to stage 02 until they have read it. Record the real conversation reference,
reviewer and exactly approved effect IDs in output/{run-id}/review.json using:

`python3 scripts/runs.py record-review RUN_ID --reviewer NAME --approval-ref REFERENCE --effects A1`

Omit --effects for a reviewed read-only deliverable. This command records an
existing approval; running it is never a way to obtain one. The snapshot covers
the review, request, selected contract and configured policy inputs. Changes
invalidate it. Source files referenced by the review must be rechecked before
effects if their contents could change; their paths alone are not identity.

## Reviewed local configuration changes

For a workflow such as signal-refresh that changes factory inputs, the exact
review includes the proposed complete file content or diff. Stage its new bytes
inside the run and compute SHA-256. Add one frontmatter line after status:
`expected_after: {"A1": {"_shared/claims.json": "64-character SHA-256"}}`.
The real value is the staged file hash, not the explanatory placeholder above.
Only named shared inputs already in the review snapshot may be changed this way.
The recorded approved IDs select which postimages are authorized. Changing a
file to any other revision invalidates review. A landed postimage without a
result is recovery_required: inspect what happened; never replay the write.

## 02 — apply and report

First run `python3 scripts/runs.py status RUN_ID`. Continue only with a current
review and the actual user authorization. Use the selected workflow and shared
rules for each approved effect. Re-read live preimages and stop the affected
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
