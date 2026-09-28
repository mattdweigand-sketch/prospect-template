# Prove public signals for a named account

## Inputs

| Kind | Path or source | Load / purpose |
|---|---|---|
| Reference | `../../.local/config/signals.md` | Discovery, classification, evidence and qualification |
| Reference | `../../.local/config/icp.md` | Target personas section |
| Reference | `../../.local/config/policy.yaml` | scan, salesforce, identity, outreach |
| Tool | `../../_shared/scripts/route_candidate.py` | Ownership route table |
| Tool | `../../_shared/scripts/evidence_gate.py`; `scan_verdict.py` | Receipt validation and report verdict; docstrings define inputs |
| Working | Named account, Salesforce reads and fetched public pages | Current source text in temporary sandbox files |

## Process

Follow `procedure.md`: resolve the account, search and verify evidence, then produce the script verdict. Read-only; talk-track content is not an input.

## Output

Concise report and one qualified bundle as fenced JSON when evidence qualifies; otherwise the reason no bundle is available. Temporary files support checks; no repo or external-system writes.

## Human check

Confirm account aliases and decide any fit objection before handing the bundle to outreach. Qualified is not approval to draft.

## Next

`../signal-outreach/` with the qualified bundle, on request.
