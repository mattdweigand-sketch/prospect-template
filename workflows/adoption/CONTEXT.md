# Check organization-level configured-product adoption

## Inputs

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Procedure | `procedure.md` | Full file | Detailed steps, report and stop conditions |
| Reference | `../../shared/providers.md` | Full file | Tool discovery, complete reads, mappings and write/readback rules |
| Settings | `../../.local/config/policy.yaml` | user_scan, crm, identity, warehouse | Installed values and boundaries |
| Tool | `../../_system/queries/adoption_lookup.sql` | Header/interface | Bindings for the reviewed private query |
| Tool | `../../_system/scripts/route_candidate.py`; `../../_system/scripts/privacy_check.py` | Route table, CLI and packet docstrings as used | Ownership routing and privacy schema |
| Working | Named Account/Id, complete CRM reads and permitted warehouse result | This account and data date | Identity and permitted adoption facts |

## Process

Step numbers match `procedure.md`; it owns the detailed rules.

1. Read scoped settings.
2. Resolve the Account and ownership route; stop for a disallowed route or unresolved identity.
3. Normalize the website domain and reject internal domains.
4. Run the verified private query read-only and fetch after successful completion.
5. Build exactly the policy-permitted bundle.
6. Run the privacy check and follow its exit status.
7. Run the Audit and report the permitted adoption statement.
8. Hand off on request within the adoption-specific outreach boundary.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 2 | Zero or multiple Account matches, when identity is unresolved | Supply the exact Account ID before the lookup |
| 7 | Permitted adoption statement, before any outreach handoff | Review the statement and request outreach; a scan alone needs no pause |

## Audit

| Check | Pass Condition |
|---|---|
| Identity | The bundle belongs to the resolved Account, normalized domain and stated data date. |
| Privacy | Only permitted aggregate fields appear and privacy_check passes. |
| Claim limits | The policy statement matches adoption; none_found adds no claim and is not proof of absence. |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Adoption report | Current chat | Procedure’s report with the permitted policy statement |
| Permitted bundle | Current chat | Privacy-checked fenced JSON |

## Next

`../../stages/03-outreach/` on request: individuals_only may use the warehouse path; org_adopted needs a qualified web signal; none_found adds no claim. A clean bundle does not approve a draft.
