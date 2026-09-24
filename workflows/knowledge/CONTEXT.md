# Knowledge workflows

Generated from scripts/wrapper-contract.json; procedures live in the linked files.

One job: route the requested knowledge task.

## Inputs
- Working: output/{run-id}/request.md and the scope and source references it names.
- Reference: one selected workflow below and its Load / Skip list.

## Process
Choose one row and follow [the run lifecycle](../run.md). Skip sibling procedures and unrelated records.

| Command | Contract | Job |
|---|---|---|
| `prospect-setup` | [prospect-setup.md](prospect-setup.md) | Run guided setup or update a team's ICP, messaging, signal mappings and email voice from its own materials. |
| `signal-refresh` | [signal-refresh.md](signal-refresh.md) | Propose claim-library updates from a configured, versioned knowledge source. |

## Outputs
The chosen workflow defines output/{run-id}/01_review.md, any declared artifacts, and 02_result.json.

## Human check
Read the workflow's exact review criteria and record review in output/{run-id}/review.json.
