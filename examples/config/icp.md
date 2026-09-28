---
territory:
  min_employees: 50
  max_employees: 10000
verticals:
- id: professional_services
  rank: 1
- id: manufacturing
  rank: 2
- id: retail
  rank: 3
disqualifiers:
  hard:
  - outside_headcount_band
  - outside_offer_scope
  - mandatory_requirement_unmet
  - required_access_unavailable
  recoverable:
  - unclear_relevant_need
---

# Fictional example ICP

This is configuration scaffolding for a generic B2B offer, not an approved target market. Setup replaces the company range, industry priorities, responsibilities and exclusions with the user's decisions. The example 50–10,000 employee band is arbitrary and is not a product requirement.

## Company parameters

Target the actual buying entity that has a need the configured offer can address. Verify its size, location, industry and purchasing scope. Preserve unknowns rather than inventing a parent/subsidiary relationship, budget or authority. Setup records geographic and other territory restrictions here when relevant.

## Target verticals and industries

The frontmatter contains three fictional priorities to illustrate ordering. Replace them with the user's markets and explain what evidence makes each market relevant. Do not infer fit solely from an industry label.

## Target personas

| Responsibility | Evidence to seek | Example search terms |
|---|---|---|
| Initiative owner | Accountable for the named project, problem or purchase | Program lead, operations director, project owner |
| Functional sponsor | Owns the affected team's outcomes | Department head, practice leader, plant manager |
| Practitioner or evaluator | Performs the relevant work or evaluates options | Team lead, specialist, evaluator |
| Commercial decision maker | Responsible for the specific budget or supplier decision | Procurement lead, business owner, finance sponsor |

Titles are search hints, not proof of responsibility or buying authority. Tailor these roles to the offer: a manufacturer, service firm and software company may have different buyers. Internal initiatives and customer-facing initiatives can both fit when the offer supports the work.

## Pursuit boundaries

An outside-scope need or unmet mandatory requirement blocks pursuit. Missing evidence of a relevant need calls for research. Setup defines offer-specific exclusions and the evidence required to resolve them. An account's activity never supplies consent, proves budget or authorizes a write.
