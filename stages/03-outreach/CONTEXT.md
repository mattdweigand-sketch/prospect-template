# Turn a qualified bundle into one outreach draft

## Inputs

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Procedure | `procedure.md` | Full file | Detailed steps, report and stop conditions |
| Reference | `../../shared/providers.md` | Full file | Tool discovery, complete reads, mappings and write/readback rules |
| Settings | `../../.local/config/policy.yaml` | outreach, approval, identity, user_scan | Installed values and boundaries |
| Reference | `../../.local/config/talk-track.md` | Core messaging, applicable Match the angle row, Claim boundaries; evidence for claims used | One supported angle |
| Reference | `../../.local/config/icp.md` | Relevant Target personas section | Recipient responsibility |
| Tool | `../../_system/scripts/outreach_gate.py`; `../../_system/scripts/readback_check.py`; `../../_system/scripts/lint_draft.py` | CLI and packet docstrings as used | Gate, native readback and advisory style review |
| Working | Qualified bundle in this thread; recipient sources and current CRM/email reads | Original bundle and complete activity reads | No reconstruction from memory or summaries |

## Process

Step numbers match `procedure.md`; it owns the detailed rules.

1. Read scoped settings, talk track and persona guidance.
2. Verify the same-thread qualified bundle and evidence freshness.
3. Verify the recipient and responsibility.
4. Read ownership, deals and complete suppression activity.
5. Choose one supported angle for that responsibility.
6. Write the draft; review meaning, claims and style.
7. Run the outreach gate.
8. Run the Audit; present exact canonical and native draft fields, with empty CC/BCC; stop.
9. After exact approval and fresh revalidation, create the draft and verify complete native message readback.
10. Enter follow-up only after the user sends manually.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 8 | Numbered To, Subject, Body, empty CC/BCC, mapped payload and supporting evidence | Approve those exact fields; any change requires a new proposal |

## Audit

| Check | Pass Condition |
|---|---|
| Recipient and angle | Responsibility is evidenced and the angle addresses the supported initiative. |
| Claims and voice | Wording respects source limits, permissions, configured voice and bundle boundaries. |
| Readiness | Current complete activity checks and the outreach gate allow this proposal. |
| Completion | Approved fields, including CC/BCC, match complete native readback. |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Draft proposal | Current chat | Numbered canonical fields, exact native payload and evidence |
| Approved draft | Native email provider | Unsent draft plus draft/message IDs and readback result |

## Next

`../04-followup/` after a proven send. The seller sends manually.
