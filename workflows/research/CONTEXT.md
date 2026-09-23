# Research workflows

Generated from scripts/wrapper-contract.json; procedures live in the linked files.

One job: route the requested research task.

## Inputs
- Working: output/{run-id}/request.md and the scope and source references it names.
- Reference: one selected workflow below and its Load / Skip list.

## Process
Choose one row and follow [the run lifecycle](../run.md). Skip sibling procedures and unrelated records.

| Command | Contract | Job |
|---|---|---|
| `signal-scan` | [signal-scan.md](signal-scan.md) | Find and qualify public buying signals for one named account. |
| `signal-user-scan` | [signal-user-scan.md](signal-user-scan.md) | Produce an organization-level adoption finding using a configured private-data adapter. |
| `signal-prospector` | [signal-prospector.md](signal-prospector.md) | Discover candidate accounts, resolve CRM ownership, and propose exact account claims. |

## Outputs
The chosen workflow defines output/{run-id}/01_review.md, any declared artifacts, and 02_result.json.

## Human check
Read the workflow's exact review criteria and record review in output/{run-id}/review.json.
