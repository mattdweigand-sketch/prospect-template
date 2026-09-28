---
workflow: signal-user-scan
reads: .local/config/policy.yaml, CRM, the configured warehouse
writes: nothing
next: signal-outreach with the privacy-checked bundle, on request
---

# signal-user-scan

Read-only. Answers one question about one account, whether the configured product is already in use there at the level a salesperson may repeat. Never reports who, how many, or when.

Read this workflow's `CONTEXT.md` before the steps. Paths below are relative to the repo root. Use temporary sandbox files for checks; never store customer material in the checkout.

## Before starting

Read `shared/providers.md` for tool discovery, complete reads, pre-write revalidation and native readback, and `CONTEXT.md` for state and resume boundaries. Run `python3 _system/scripts/preflight.py signal-user-scan`. Missing active configuration routes to `prospect-setup`; disabled optional modules stop. Verify that the tools required for the next step are actually available.

## Steps

1. Read `.local/config/policy.yaml` (`user_scan`, `crm`, `identity`, `warehouse`). Never restate its values in the report.
2. Resolve the account in CRM. Query Account by Id or Name. Record Id, Name, Website, owner_id, owner_is_active, and open deals per `policy.crm.open_deal`. Route per the `_system/scripts/route_candidate.py` route table. Anything but `scan` stops and reports the route (`active_deal` or `owned_elsewhere`). Zero or many matches is a finding. Ask which Id before continuing.
3. Derive the domain from Website. Strip scheme, `www.`, and path. Lowercase. If the domain is in `policy.identity.internal_domains`, stop.
4. Run the hash-verified private SQL copy named by `policy.warehouse.queries.adoption_lookup.path` through the configured warehouse tools, read-only, async, warehouse `policy.warehouse.name`. Bind the Account Id, the domain, and `policy.warehouse.data_date` in header order. Fetch the one result row only after status is success.
5. Build the bundle with exactly the keys in `policy.user_scan.bundle_keys`. Split comma lists into arrays, empty string to `[]`. Cast `mapped_org_count` to int. Set `adoption` to one value from `policy.user_scan.adoption_values` by the rule noted beside that key. Save to a file.
6. Run `python3 _system/scripts/privacy_check.py --bundle <file>`. Exit 0 is required. Exit 1 means fix the bundle, never the check. Exit 2 means stop.
7. Report in the format below. The only adoption claim outreach may repeat is the `policy.user_scan.statements` entry keyed by `adoption`.
8. Hand off on request. An `individuals_only` bundle can use the existing warehouse outreach path. An `org_adopted` bundle is optional context alongside a qualified web signal, not a standalone outreach signal. `none_found` supplies no adoption claim. Clean is not approval to draft or contact anyone.

## Report

```
Account: <name> | CRM: <Id> | Owner: <name, active/inactive> | Route: scan / active_deal / owned_elsewhere
Domain: <domain> | Data through: <date>
Adoption: org_adopted / individuals_only / none_found
  Org subscription mapped to this Account: yes/no (<service types>, <platforms>) or none
  Paid individual subscribers at <domain>: yes/no
Privacy check: clean
```json
<bundle>
```
none_found: no mapped org and no paid individuals on the data date. Not proof of absence. The org may be mapped to a duplicate Account.
Next: individuals_only may go to signal-outreach; org_adopted needs a qualified web signal; none_found adds no claim.
```

## Refuse

- Any field in `policy.warehouse.forbidden`. Not in the report, not in chat, not roughly.
- Editing the query to add columns. Change the policy and the check first, in a separate approved edit.
- Any write to CRM, the configured warehouse, email provider, or checkout files.
- Drafting or wording a message. That is `signal-outreach`.
