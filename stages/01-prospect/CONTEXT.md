# Find net-new accounts and propose CRM claims

## Inputs

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Procedure | `procedure.md` | Full file | Detailed steps, report and stop conditions |
| Reference | `../../shared/providers.md` | Full file | Tool discovery, complete reads, mappings and write/readback rules |
| Settings | `../../.local/config/policy.yaml` | prospector, crm, scan, identity, warehouse | Installed values and boundaries |
| Reference | `../../.local/config/icp.md` | Company, industry, personas and territory metadata | Account and contact fit |
| Reference | `../../.local/config/signals.md` | Discovery and qualification | Source selection and interpretation |
| Tool | `../../_system/queries/adoption_territory.sql` | Header/interface only, when enabled | Map reviewed private SQL; do not run the example as production SQL |
| Tool | `../../_system/scripts/evidence_gate.py`; `../../_system/scripts/route_candidate.py`; `../../_system/scripts/readback_check.py` | CLI and packet docstrings as used | Evidence, routing and readback checks |
| Working | Current web evidence, permitted warehouse rows and CRM records | This run; all required pages | Sources and completed-read evidence |

## Process

Step numbers match `procedure.md`; it owns the detailed rules.

1. Read scoped settings, signals and ICP.
2. Discover public signals and optional adoption candidates; deduplicate.
3. Run the evidence gate for each web candidate.
4. Verify headcount against a permitted source.
5. Read complete CRM Account, Contact and deal records.
6. Route candidates; continue only for eligible claims.
7. Verify contact responsibility, address and sources.
8. Map exact native payloads, run the Audit, and present numbered proposals; stop for approval.
9. After exact approval and fresh revalidation, write and verify full native readback.
10. Hand off verified claims and qualified bundles only on request.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 8 | Numbered Account/Contact fields, sources, transfer reason and native payloads | Approve exact writes; a newly resolved Account ID needs review before its Contact write |

## Audit

| Check | Pass Condition |
|---|---|
| Fit and evidence | Source meaning supports offer fit and the evidenced contact responsibility. |
| Eligibility | Complete reads and checks support routing, territory and headcount. |
| Proposal | Canonical and native fields, associations and source support are visible before approval. |
| Completion | Approved fields match complete readback; uncertainty stops further writes. |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Claim proposals | Current chat | Numbered fields, native payloads and sources |
| Approved claims | Native CRM | Records with IDs and complete readback |
| Qualified handoff | Current chat | Verified claim plus unchanged gate bundle |

## Next

`../02-research/` for eligible adoption leads; `../03-outreach/` for verified claims with qualified bundles, on request.
