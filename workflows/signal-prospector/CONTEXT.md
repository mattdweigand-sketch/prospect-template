# Find net-new accounts and propose CRM claims

## Inputs

| Kind | Path or source | Load / purpose |
|---|---|---|
| Reference | `../../.local/config/icp.md` | Company, industry and persona guidance; territory and routing metadata |
| Reference | `../../.local/config/signals.md` | Discovery categories, evidence interpretation and qualification |
| Reference | `../../.local/config/policy.yaml` | prospector, crm, scan, identity, warehouse |
| Tool | `adoption_territory.sql` | Read-only discovery query; bindings in its header |
| Tool | `../../_shared/scripts/evidence_gate.py`; `../../_shared/scripts/route_candidate.py`; `../../_shared/scripts/readback_check.py` | Evidence, routing and approved-field readback; docstrings define inputs |
| Working | Current web evidence, warehouse rows and CRM Account/Contact/deal reads | This run only; preserve sources and completed-read evidence |

## Process

Follow `procedure.md`: discover, prove evidence, route candidates and propose exact Account/Contact claims.

## Output

Numbered proposals in the thread; approved claims in CRM with readback. Verified claims include their qualified bundle. No files are written to this folder.

## Human check

Approve each exact write by number. A claim does not approve a draft or contact.

## Next

`../signal-scan/` for eligible adoption leads; `../signal-outreach/` for verified claims with qualified bundles, on request.
