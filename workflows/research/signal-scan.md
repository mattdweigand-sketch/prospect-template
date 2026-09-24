# Public signal scan

Use for one named account, including a request about a named person there.
Research and qualification are read-only. This workflow creates no messages.

## Load / Skip

- Working: output/{run-id}/request.md; only an explicitly named source run.
- Reference: workflows/run.md, _shared/rules.md; policy.json identity, scan, routing and outreach.activity_lookback_days; taxonomy.json tier 1/2 web entries; adapters.md CRM account, opportunity and task reads and public fetch.
- Skip: claims.json, private adoption and billing data, mail, team chat, knowledge repositories and other accounts. The public report may continue without CRM, but must say ownership and activity are unverified and cannot hand off an actionable outreach bundle.

## Process

1. Resolve the buying entity by CRM name and website domain. Read account ID, name, website, owner ID/name/active status, and all open opportunities using the configured predicate. Zero or multiple matches are findings: continue public research using the supplied name, but resolve identity before outreach. Any open opportunity stops the account as `active_deal` and hands it to the sales owner.
2. Read account tasks covering `max(outreach.activity_lookback_days, scan.warm_engagement.lookback_days)`. Retain the complete read reference, earliest covered date and tasks with ID, owner, subject and aware creation timestamp in the CRM packet defined by `scripts/route_candidate.py:scan_route`. Preflight evaluates that route, including the warm window, configured owner exclusions and open-deal precedence. Show other-rep activity and each warm task's subject, owner and date. Insufficient coverage or unresolved CRM identity permits a limited report only; other ownership never grants permission to claim or contact.
3. Declare account-owned aliases from the account website or fetched sources: brands, subsidiaries and named executives with their roles. The user must confirm the relationship before an outreach handoff. Do not treat a vendor's customer, a partner or an unrelated quoted person as an alias.
4. Print the full query list **before searching**, one query for every tier 1 and tier 2 web signal type, using its example_queries and the account name. Use each type's freshness window. Search account-wide even when a person was named. Prefer internal use, concrete company actions, mandates and the account's own words over marketing about products it sells. Adoption entries are not web queries.
5. Choose at most scan.max_signals_per_account sources. Fetch each page in full; retain URL, source name, actual read timestamp and page text in this run. Snippets, memory and summaries cannot serve as quotes. Record failed fetches and uncovered types rather than calling them absent.
6. Write one receipt with account_name, account_domain, nonempty account_aliases, source_url, quote, evidence_subject, quote_speaker, signal_type, published_date and event_date. quote_speaker is account for direct account/alias words and third_party for someone else's paraphrase. A null publication date requires a live page on the account domain or its subdomain that explicitly dates the event; an undated evergreen page cannot qualify. The evidence_subject is whose action the quote actually establishes.
7. Run `python3 scripts/evidence_gate.py --receipt output/RUN_ID/receipt.json --page output/RUN_ID/source.txt --checked-at FETCH_TIMESTAMP`. The gate requires a taxonomy source of web and evaluates dates in identity.timezone. Save its JSON output per source. Exit 0 provides a qualified bundle; exit 1 is an unusable finding; exit 2 requires fixing the input or stopping that source. Do not change facts to pass. Check semantic fit separately: dates, attribution and verbatim matching do not prove that the quote satisfies the signal definition.
8. Run `python3 scripts/scan_verdict.py OUTPUT_1.json OUTPUT_2.json` in report order. Copy its verdict and next lines exactly. One qualified signal suffices for a scan; the prospector admission rule does not apply. A semantic objection remains on that item as `Rejected on fit, reason`; it does not silently change the machine verdict. Show the recommended bundle even if it has an objection so the reviewer can decide.

## Outputs and readiness

Save output/{run-id}/01_review.md with CRM resolution and route, other-rep activity, aliases, optional direct/indirect/no connection to the named person, query coverage and number of full sources checked. Use numbered findings with event/publication date, what happened, why it matters, the exact attributed quote, outcome/rejection reason and a source link. Include stale age/window, undated and third-party warnings where applicable.

End with the gate's verdict and next lines, a known next dated trigger if any, and fenced JSON for **only the recommended signal**. Declare each receipt, fetched text and gate output in the review's artifacts list. A partial read can produce a clearly limited research finding, never a claim of absence or a ready external effect. There are no effect headings.

In inputs.json, list `sources` as `{receipt, page, result, checked_at}` entries with unique run-relative filenames per source; checked_at may instead be in the receipt. Set `crm` to the retained CRM packet path and optionally `verdict` to a saved verdict. Run `runs.py preflight RUN_ID` before review. It rechecks actual fetch times, sources and CRM coverage and binds the selected signal to the resolved entity. Record unavailable inputs in `gaps`; only the derived eligible export may support outreach. Manifest inputs are snapshotted automatically; the artifacts list is for additional review material.

## Human check

Review entity/alias ownership, attribution, signal fit, query gaps and CRM route. Follow workflows/run.md to record the reviewed finding. A requested handoff names this exact run, bundle and review reference. Qualification or review of research does not authorize an email draft. No provider writes, adoption lookups or drafting occur here.
