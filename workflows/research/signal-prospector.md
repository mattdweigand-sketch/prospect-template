# Prospect discovery and account claims

Discover candidate accounts, verify their evidence and territory, and propose exact CRM account/contact changes.

## Load / Skip

- Working: output/{run-id}/request.md, named territory and filters.
- Reference: workflows/run.md, _shared/rules.md; policy.json identity, scan, routing, prospector and adoption enablement; taxonomy.json; icp.md frontmatter; adapters.md public research, CRM claim mappings, verified enrichment and optionally adoption_territory.
- Skip: mail, team chat, billing growth, claims.json and the knowledge source. If adoption is disabled, continue public discovery and show that source as unavailable.

## Process

1. Print and run one discovery query per tier 1/2 **web** type, using example_queries without a company name. Prefer fresh evidence, named executive actions and distinct companies; remove internal domains/subdomains.
2. Optionally run the reviewed adoption_territory adapter read-only for the owner, complete data date, territory and prospector.adoption_candidate_rows. Wait for confirmed success. It returns only aggregate leads on already-owned accounts. A paid_individuals_present lead admits only alongside one qualified **web Tier 2** signal found for that account in this run; search those companies too. No user-level fields, counts or unrelated warehouse reads.
3. Keep at most prospector.max_candidates candidates, preferring Tier 1 evidence and named executive actions. Record sources searched, companies seen, candidates retained and gaps. This cap is not an excuse to fabricate coverage.
4. For each public signal, fetch the full page, save its receipt/text/read timestamp, and run evidence_gate.py as specified in signal-scan's receipt contract. Only exit 0 bundles count; read semantic fit against the selected taxonomy definition. The fixed admission rule and distinct-type counting are owned by `scripts/route_candidate.py:admission`; its adoption exception also applies. Do not add a threshold in policy or choose a different rule for this run.
5. Verify buying-entity headcount from the first dated reliable hit in prospector.headcount_sources order. Keep the source/date and entity scope; unknown stays null. Assign a supported icp.md vertical or null and only evidenced disqualifier IDs. Hard disqualifiers prevent claims; recoverable blockers remain visible.
6. Query CRM by both name and website domain. Read account ID/name/website, owner ID/name/active status, open opportunities using the configured predicate, and all contacts on the matched account. Resolve multiple matches before proposing a write. Do not treat a replica owner, a missing read or an omitted opportunity list as current CRM state.
7. Save a routing receipt (scripts/route_candidate.py docstring) and run `python3 scripts/route_candidate.py --receipt output/RUN_ID/candidate.json`. Report admission, territory, vertical rank, hard/recoverable blockers, route and claimable. Any open deal routes active_deal before ownership logic. Unknown/out-of-territory headcount cannot be claimed. Other active owners route owned_elsewhere; only configured house owners or inactive owners are transferable. Already-owned/no-deal accounts route scan, including all adoption leads, and are never claimed again.
8. Only for claimable candidates, find at most one contact. Prefer the named signal person, then the configured contact_email_sources order: existing CRM contact followed by verified enrichment. Inspect no more than prospector.max_people_per_account people. A missing verified address means account-only; never infer a name or build an email pattern. An existing contact is reused, not recreated.
9. Propose each permitted effect separately: account creation, exact owner transfer, or contact creation attached to that account. Use adapters.md's allowed fields and show **every native field/value and its source**. A transfer includes current owner/name/status and inactive/house justification. A new-account contact references the account effect as a dependency; explain how the returned ID fills that one field. No arbitrary CRM fields or other write types are allowed.
10. After exact review under workflows/run.md, refresh the account/domain duplicate search, owner, opportunities, headcount evidence and contact match. If any preimage changes, revise the affected proposal. Apply one approved record per call, only after its dependencies verify. Query every returned ID and compare every approved field. Report uncertainty or mismatch without silent repair or blind retries.

## Outputs and readiness

The review has run/date, search coverage, all candidate routes with supporting quotes/dates/links, headcount source, blockers and exact numbered `Effect` proposals. Declare page/receipt/bundle/routing outputs and permissible CRM read receipts as artifacts. Missing sources keep the affected effect in draft; no claimable candidates is a finding, not proof the territory is empty.

In inputs.json, retain `sources` entries `{receipt, page, result, checked_at}` and `candidates` entries `{receipt, result, sources}`. A candidate's sources names its source-result paths; its routing receipt includes the existing account_id when linking adoption evidence. Optional `contact` names a file containing first_name, last_name, title, verified email and source_reference; optional `adoption` is the exact reviewed aggregate handoff defined in workflows/run.md. Public signal associations precede the adoption signal in the routing receipt. Bind each Effect to its candidate receipt with kind account_create, owner_transfer or contact_create; a new-account contact also names its account_effect. Preflight rechecks source/account/type associations and eligibility. Held candidates remain findings and cannot supply effect bindings.

After application, 02_result.json accounts for each approved effect and readback. Hand off verified claims and their qualified bundles by exact run/reference to outreach on request. CRM remains the account/contact record; the local review is not a prospect ledger.

## Human check

Review entity, signal fit, territory, ownership, verified contact source and every field. Each effect needs approval, which may cover an exact list together. Claim approval grants no permission to draft or contact. Never create opportunities, tasks, email drafts or messages; never merge/delete records or continue a claim on an open deal.
