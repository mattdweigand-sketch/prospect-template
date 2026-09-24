# Outreach workflows

Generated from scripts/wrapper-contract.json; procedures live in the linked files.

One job: route the requested outreach task.

## Inputs
- Working: output/{run-id}/request.md and the scope and source references it names.
- Reference: one selected workflow below and its Load / Skip list.

## Process
Choose one row and follow [the run lifecycle](../run.md). Skip sibling procedures and unrelated records.

| Command | Contract | Job |
|---|---|---|
| `signal-outreach` | [signal-outreach.md](signal-outreach.md) | Prepare one evidence-backed cold email and create an unsent draft after exact approval. |
| `signal-followup` | [signal-followup.md](signal-followup.md) | Create one CRM follow-up task after a uniquely identified email was actually sent. |
| `signal-arr-growth` | [signal-arr-growth.md](signal-arr-growth.md) | Optional subscription module: find self-service ARR growth accounts and propose configured template drafts. |

## Outputs
The chosen workflow defines output/{run-id}/01_review.md, any declared artifacts, and 02_result.json.

## Human check
Read the workflow's exact review criteria and record review in output/{run-id}/review.json.
