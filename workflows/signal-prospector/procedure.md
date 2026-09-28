---
workflow: signal-prospector
reads: .local/config/policy.yaml, .local/config/signals.md, .local/config/icp.md, web, the configured warehouse, CRM
writes: CRM Account and Contact claims, one approval each
next: signal-scan for eligible adoption rows, signal-outreach for verified claims
---

# signal-prospector

Discovers companies showing the configured buying signals, proves the evidence, routes each against CRM, and proposes claims. Every CRM write is a numbered proposal with its own approval. Writes nothing else anywhere.

Read this workflow's `CONTEXT.md` before the steps. Paths below are relative to the repo root. Use temporary sandbox files for checks; never store customer material in the checkout.

## Before starting

Read `setup/providers.md` for tool discovery, complete reads, pre-write revalidation and native readback, and `CONTEXT.md` for state and resume boundaries. Run `python3 scripts/preflight.py signal-prospector`. Missing active configuration routes to `prospect-setup`; disabled optional modules stop. Verify that the tools required for the next step are actually available.

## Steps

1. Read `.local/config/policy.yaml` (`prospector`, `crm`, `scan`, `identity`, `warehouse`), `.local/config/signals.md`, and `.local/config/icp.md`. Never restate their values in the report.
2. Discover. Two sources. Web. Search every discovery category in `.local/config/signals.md` with no company name, using its Where to look and Evidence to capture columns. Include public executive LinkedIn posts. Record coverage and access gaps. Classify each finding as `active_initiative`, `early_indication`, or `general_mention`, and relevance as `relevant_to_offer`, `outside_offer`, or `unclear`. Keep useful discovery findings even when they do not qualify. Only source-proven active offer-relevant evidence meeting the Qualification section and frontmatter gates counts toward a claim. Use the applicable frontmatter `freshness_days` for automated qualification; a discovery finding may remain useful outside it. Collect distinct companies. Drop companies whose domain is in `policy.identity.internal_domains`. Adoption (only when `policy.prospector.adoption_source.enabled` is true; otherwise record this source disabled). Run the hash-verified private SQL copy named by `policy.warehouse.queries.adoption_territory.path` through the configured warehouse tools, read-only, async, warehouse `policy.warehouse.name`, with the five bindings named in its header, `policy.warehouse.data_date` first. Fetch rows only after status is success. Each row is a `policy.prospector.adoption_source.signal_type` lead on an Account the seller already owns. Report only the row's fields, never anything in `policy.warehouse.forbidden`. Before per-company enrichment, merge and deduplicate both sources and keep at most `policy.prospector.max_candidates_per_run` candidates, preferring tier1 evidence and named executive actions. For retained adoption candidates, search the web too: their admission pairing rule is the taxonomy `admission` block, enforced by `route_candidate.py`.
3. Prove each web signal the signal-scan way. Warehouse evidence remains the SQL-derived row from step 2. Fetch the page in full, save the text, write a receipt, run `python3 _shared/scripts/evidence_gate.py --receipt <r.json> --page <page.txt>`. Only exit 0 bundles count. A snippet is never evidence.
4. Verify headcount of the buying entity from the first dated source found in `policy.prospector.headcount_sources` order. Record the source. Unknown stays null.
5. Read CRM. Query accounts by name and website domain, normalizing `id, name, website, owner_id, owner_name, owner_is_active` and a complete related-deal read classified by `policy.crm.open_deal`. Also query Contacts on any matching Account.
6. Route. Write one receipt per candidate (shape in the script docstring). Set `vertical` to the `icp.md` frontmatter id the evidence supports, null when unsure. List `disqualifiers` ids the evidence shows. Run `python3 _shared/scripts/route_candidate.py --receipt <c.json>`. Its docstring is the route table. Report every route with its vertical rank and blockers. Only `claimable: true` proceeds. Eligible adoption rows route `scan` and are handed to `signal-scan`, never claimed.
7. Find one Contact per claimable candidate. Prefer the person named in the signal when their responsibility is relevant. Otherwise use the ICP persona tables to find the initiative owner or functional sponsor. Titles are search aids; verify responsibility from a source and explain the choice. Do not map to legacy persona IDs or assume authority from seniority. Sources in `policy.prospector.contact_email_sources` order. Look up at most `policy.prospector.max_people_per_account` people. No verified email means no Contact proposal. Never guess an address or a name.
8. Propose. Map approved canonical create/update fields with `crm.account.write`, `crm.owner.write`, or `crm.contact.write` before presenting the exact native payload. After creation, normalize the returned record with its `.read` mapping and compare every approved field and relationship. Account creation may yield the ID needed for a contact proposal: show that resolved target before approving the contact write. No unknown account ID can be treated as already approved. Number each write. Show every field from `policy.prospector.account_fields` or `policy.prospector.contact_fields` with its value and source. A `claim_transfer` shows current owner name, status, and the reason it is claimable (inactive or house owner). Stop and wait.
9. Write only what was approved, one record per call. After each write, query the record by Id (`policy.approval.readback_required`). Run `python3 _shared/scripts/readback_check.py --expected <approved-fields.json> --actual <normalized-native-readback.json>` against every approved field and show the result. Extract fields only from the native return; never reconstruct readback from the proposal. A mismatch stops the run and is reported, not repaired or retried automatically.
10. Hand off. For each verified claim, print the qualified signal bundle as fenced JSON for `signal-outreach`. A claim is not approval to draft or contact anyone.

## Report

```
Run: <date> | Searched: <n signal types> | Companies seen: <n> | Candidates: <n>

Candidate 1: <company> | <domain> | headcount <n> (<source>) | CRM: <Id or none> | Route: <route> | Claimable: yes/no
  Signal: <signal_type> (<tier>) | <published_date>
  "<quote>"
  <source_url>
Candidate 2: <company> | ... | Route: owned_elsewhere (<owner name>, active). Skipped.

Discovery-only: <initiative, stage, classification, relevance, source and why it does not qualify; outside-offer findings separately>

Proposals (each needs its own approval):
1. Create Account: Name <..>, Website <..>, owner_id <the seller>, headcount <n>
2. Create Contact on proposal 1: first_name <..>, last_name <..>, Title <..> (responsibility <supported description or unresolved>), Email <..> (source: <..>)
3. Update Account <Id>: owner_id <house id> -> <the seller>. Owner today: <name>, <inactive/house>.

Nothing claimable: <reason per candidate>. Not proof the territory is empty.
```

## Refuse

- Any CRM write not listed in `policy.prospector.claim_writes` or named in `policy.approval.never`.
- A claim on any route other than `claim_new` or `claim_transfer`.
- Drafting or sending any message. That is `signal-outreach`.
- Reading email provider or Slack. Reading anything in the configured warehouse beyond the reviewed private query corresponding to `workflows/signal-prospector/adoption_territory.sql`, or any field in `policy.warehouse.forbidden`.
- Ledgers, run records, or any file written to the project. CRM is the record of what was claimed.
