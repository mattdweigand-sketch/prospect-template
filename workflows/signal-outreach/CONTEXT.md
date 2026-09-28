# Turn a qualified bundle into one outreach draft

## Inputs

| Kind | Path or source | Load / purpose |
|---|---|---|
| Reference | `../../.local/config/policy.yaml` | outreach, approval, identity, user_scan |
| Reference | `../../.local/config/talk-track.md` | Core messaging, applicable Match the angle row, Claim boundaries; supporting evidence only for claims used |
| Reference | `../../.local/config/icp.md` | Relevant Target personas section |
| Tool | `outreach_gate.py`; `../../_shared/scripts/readback_check.py` | Packet checks and approved-field readback |
| Tool | `../../scripts/lint_draft.py` | Bundled advisory style review |
| Working | Qualified bundle in this thread; recipient sources and current CRM/email provider activity reads | No bundle reconstruction from memory or summaries |

## Process

Follow `procedure.md`: verify the recipient responsibility, choose one angle, check activity and wording, then propose exact draft fields. Discovery catalog content is not an input.

## Output

One numbered proposal in the thread; one email draft after approval and exact readback. Nothing is written to this folder.

## Human check

Approve exact To, Subject and Body. A passing gate does not establish source meaning, recipient fit or claim support. the seller sends manually.

## Next

`../signal-followup/` after a proven send.
