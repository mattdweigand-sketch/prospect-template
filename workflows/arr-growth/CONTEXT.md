# Propose fixed-template drafts for self-serve ARR growth

## Inputs

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Procedure | `procedure.md` | Full file | Detailed steps, report and stop conditions |
| Reference | `../../shared/providers.md` | Full file | Tool discovery, complete reads, mappings and write/readback rules |
| Settings | `../../.local/config/policy.yaml` | identity, approval, crm, arr_growth, warehouse, prospector.headcount_sources, outreach.suppressing_task_subtypes | Installed values and boundaries |
| Machine settings | `../../.local/config/icp.md` | Territory metadata only; agent need not load the body | Gate territory checks |
| Tool | `../../_system/queries/arr_growth_source.sql` | Header/interface | Reviewed private query’s USD and coverage contract |
| Tool | `../../_system/scripts/arr_growth_gate.py`; `../../_system/scripts/route_candidate.py`; `../../_system/scripts/readback_check.py` | CLI, routing and packet docstrings as used | Eligibility, fixed copy and approved-field readback |
| Working | USD-normalized warehouse rows and current CRM/email reads | Explicit currency, complete routing/contact/suppression evidence | Candidate eligibility |

## Process

Step numbers match `procedure.md`; it owns the detailed rules.

1. Read scoped settings.
2. Run the verified private query; preserve explicit USD and stop when no candidates exist.
3. Resolve CRM ownership and open-deal routing.
4. Verify headcount from a permitted source.
5. Resolve contacts and complete all suppression reads.
6. Run the growth gate on the complete candidate packet.
7. Run the Audit; present each exact gate draft and native payload with empty CC/BCC; stop.
8. After exact approval and fresh revalidation, create each approved draft and verify full native readback.
9. Enter follow-up in ARR mode only after a proven send.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 7 | Numbered recipient, subject, body, empty CC/BCC and mapped native payload | Approve each exact draft separately; changed fields require a new proposal |

## Audit

| Check | Pass Condition |
|---|---|
| Eligibility | Explicit USD, daily coverage, arithmetic, routing, territory and suppression pass the gate. |
| Copy | Draft fields match the policy template and gate output; no invented growth claims. |
| Completion | Each approved draft matches complete native message readback, including CC/BCC. |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Draft proposals | Current chat | Numbered fixed-template drafts and exact native fields |
| Approved drafts | Native email provider | Unsent drafts with draft/message IDs and readback results |

## Next

`../../stages/04-followup/` in arr_growth mode after a proven send. The seller sends manually.
