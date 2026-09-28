# Check organization-level configured-product adoption

## Inputs

| Kind | Path or source | Load / purpose |
|---|---|---|
| Reference | `../../.local/config/policy.yaml` | user_scan, crm, identity, warehouse |
| Tool | `../../_shared/scripts/route_candidate.py` | Ownership route table |
| Tool | `adoption_lookup.sql` | Read-only adoption query; bindings in its header |
| Tool | `../../_shared/scripts/privacy_check.py` | Bundle schema and privacy checks |
| Working | Named Account/Id, CRM reads and the warehouse query result | This run only; ambiguous Account matches require an Id |

## Process

Follow `procedure.md`: resolve the Account, read permitted adoption facts and privacy-check the bundle. Read-only; no ICP or talk-track body is required.

## Output

Adoption report and privacy-checked bundle as fenced JSON in the thread. No repo or external-system writes.

## Human check

Resolve ambiguous Account identity before the lookup. Review the permitted adoption statement before any outreach handoff; a clean bundle is not approval to draft.

## Next

`../signal-outreach/` on request: individuals_only can use the warehouse path; org_adopted needs a qualified web signal; none_found adds no claim.
