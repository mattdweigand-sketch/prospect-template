---
type: synthetic-example
status: draft
artifacts: []
---
# Example review

Fabricated demonstration data. This provisional review has no live run,
verified recipient, claim approval or authorization.

## Scope and source coverage

One fictional account, Example Account, at example.org. No external service
was queried. The local [source fixture](source.txt) says:

> Example Account announced a reporting initiative on 2026-01-10.

This fixed fixture has no live fetch timestamp or qualified evidence bundle.

## Findings or deliverable

The announced reporting initiative suggests an evaluation of reporting tools.
An operations lead may own that work; the role and need for CSV are hypotheses.

| Review field | Illustrative value |
|---|---|
| Signal | reporting_initiative |
| Vertical / persona | technology / operations_owner |
| Claim | csv_export, from [the example library](../_shared/claims.example.json) |
| Claim boundary | Fictional CSV export capability; no accuracy, time-saving or integration promise |
| Selection | bound to the signal in [the example taxonomy](../_shared/taxonomy.example.json) |
| Runner-up | none; the example library contains one claim |
| Relevance | exploratory; the source does not mention CSV |
| claim.pick_reason | The announced reporting initiative makes report export a plausible evaluation topic for the CSV export claim, though CSV need remains an inference. |
| Recipient source / title | synthetic address; Operations title assumed, unverified |
| Activity coverage | missing; no CRM or sent-mail reads |
| voice_anchor_reference | missing; provisional wording only |
| Gate result / fit flags | not run; example units are unapproved |

## Effect A1

Illustrative destination: configured mail adapter, new unsent draft.
Native provider fields must be resolved before a live review can be ready.

**To:** buyer@example.org

**Subject:** Reporting exports

**Body:**

```text
Hi Alex,

Your reporting initiative caught my attention. Example Product can export reports in CSV format.

Would a CSV export be useful as you evaluate the reporting process?
```

## Checks and unresolved work

- Cut list: omit any promised time savings, assumed integration or invented prior conversation.
- Thin spots: CSV need and the recipient's ownership are unverified inferences.
- Before a live review: configure and approve the factory, qualify fresh public
  evidence, verify the account and recipient, complete activity reads, supply a
  voice anchor and run the workflow checks. Declare the exact supporting files
  as artifacts and obtain human approval of the complete effect.

This example creates no provider effect. Use an isolated run for testing.
