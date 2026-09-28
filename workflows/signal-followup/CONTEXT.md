# Log one proven send as an open CRM Task

## Inputs

| Kind | Path or source | Load / purpose |
|---|---|---|
| Reference | `../../.local/config/policy.yaml` | identity, approval, followup |
| Tool | `followup_gate.py`; `../../_shared/scripts/readback_check.py` | Task packet validation and approved-field readback |
| Working | Live email provider sent-mail proof; CRM Account, Contact and Task reads; outreach verdict in this thread | Historical angle/unit labels remain valid; use arr_growth mode only for a demonstrated ARR-growth send |

## Process

Follow `procedure.md`: prove the send, resolve the Account and Contact, check duplicates and propose the exact Task. A draft or thread summary is not sent-mail proof.

## Output

One numbered Task proposal; after approval, one CRM Task read back by Id. Nothing is written to this folder.

## Human check

Approve exact Task fields. Changing a field, recipient or sent message requires a new proposal.

## Next

None. CRM holds the record.
