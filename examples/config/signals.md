---
admission:
  tier1_min: 1
  tier2_min: 2
  warehouse_needs_web_tier2: true
  warehouse_max_counted: 1
tiers:
  tier1:
  - id: relevant_leader_appointment
    freshness_days: 90
  - id: announced_initiative
    freshness_days: 60
  - id: relevant_procurement
    freshness_days: 45
  - id: funded_priority
    freshness_days: 90
  - id: supplier_standardization
    freshness_days: 120
  - id: operating_change
    freshness_days: 90
  tier2:
  - id: relevant_hiring_cluster
    freshness_days: 30
  - id: leader_priority_statement
    freshness_days: 60
  - id: relevant_partnership
    freshness_days: 90
  - id: earmarked_investment
    freshness_days: 120
  - id: paid_individuals_present
    freshness_days: 1
    source: workflows/signal-prospector/adoption_territory.sql
  tier3:
  - id: generic_marketing
  - id: single_job_post
  - id: industry_trend_mention
  - id: discovery_only
---

# Fictional example buying signals

Configure signals around the buyer's work and this offer. These neutral examples are starting points, not evidence that every appointment, hiring event or funding round is relevant. Setup must choose and define the applicable signals, freshness windows, qualification thresholds and example search queries.

## Signals to look for

| Signal | Where to look | Evidence to capture |
|---|---|---|
| Announced project or change | Company announcements, project pages, public reporting | Specific initiative, stage, scope, owner and timing |
| New responsibility | Leadership announcements, role descriptions, public posts | Named person and a mandate related to the offer |
| Procurement or supplier evaluation | RFPs, tender notices, purchasing pages | Relevant requirement, buying entity, deadline and evaluation owner |
| Hiring for delivery | Careers pages and substantive job descriptions | Work the role will deliver, not merely a skill keyword |
| Investment or budget | Company statements, investor materials, public budgets | Funding explicitly linked to a relevant initiative |
| Expansion or operating change | Location announcements, service launches, partner news | Work created by the change and the team accountable for it |
| Stated need or implementation experience | Firsthand posts, interviews, customer stories | Attributed problem, intent or activity within the speaker's actual scope |

Search with the configured offer's buyer terminology. Example query shapes: company name plus initiative terms; relevant problem plus procurement or hiring; executive name plus the responsibility being researched. Read full sources; snippets only locate evidence.

## Interpret the evidence

- **active_initiative:** A specific, current project, evaluation, purchase, implementation or expansion. Describe the actual stage; hiring does not establish deployment.
- **early_indication:** A specific intent or possible need whose execution remains unclear.
- **general_mention:** Commentary or marketing without a specific company action.

## Decide relevance to the offer

- **relevant_to_offer:** The evidenced work is within the configured offer's scope. State a `fit_reason` connecting the source to an explicit offer capability or deliverable and its limits.
- **outside_offer:** The source describes work the configured offer does not support. Report the finding without an outreach handoff.
- **unclear:** More research is needed to establish fit.

An initiative can serve employees, customers, partners or physical operations. Its audience alone does not decide fit. The same source may be relevant to one offer and outside another. Do not infer pain, dissatisfaction, budget, purchase intent or authority from a signal. Qualification requires both an active initiative and evidenced offer relevance; code checks the stated judgment, not its semantic truth.

## Check whether the initiative is current

Record the source date and check time. Verify open roles, procurement windows and continuing implementation. Use the frontmatter freshness window for each configured signal. Missing dates or uncertain status remain unknown. Count one underlying initiative once, even if several sources repeat it.

## Qualification for automated workflows

The definitions below are fictional examples and must be tailored during setup. A signal identifier is a label, not an independent proof of the definition.

| Identifier | Evidence needed, in addition to active initiative and offer fit |
|---|---|
| `relevant_leader_appointment` | A named appointment with an explicit mandate related to the configured offer |
| `announced_initiative` | A company-announced project with a concrete timeline, workflow, location, team or budget |
| `relevant_procurement` | A procurement or evaluation notice whose requirements match the offer |
| `funded_priority` | A specific commitment of resources to relevant work |
| `supplier_standardization` | An actual supplier or operating-standard decision relevant to the offer; do not infer dissatisfaction |
| `operating_change` | A specific operating-process, policy or responsibility change creating relevant work |
| `relevant_hiring_cluster` | Two or more current roles delivering the same relevant initiative; one substantive role can still be useful discovery |
| `leader_priority_statement` | A named leader describing a specific relevant need, evaluation or implementation |
| `relevant_partnership` | A partnership or pilot with a demonstrated connection to the buyer's own relevant project |
| `earmarked_investment` | Investment explicitly assigned to relevant work, rather than a general funding announcement |
| `paid_individuals_present` | Optional subscription-module evidence only, under the privacy and warehouse rules below |

Tier 3 labels (`generic_marketing`, `single_job_post`, `industry_trend_mention`, `discovery_only`) do not qualify. Named-account scans may hand off one qualified signal. New-account claims use the configured admission thresholds and distinct-initiative rule. Neither result authorizes a write.

## Optional subscription evidence

Use this section only when the seller's business has individual and organizational subscriptions and the corresponding module is enabled. Otherwise leave these paths disabled and make no adoption or spend claim.

Account adoption, paid-individual presence and growing organizational recurring revenue require authorized, complete warehouse reads using reviewed mappings. Public mentions do not substitute. Permitted adoption wording comes only from the installed policy. Individual identity, counts, query content and usage timing must not be exposed. ARR and billing-source details remain internal. Empty results do not prove absence.

## Record and use findings

Keep account, initiative/stage, owner or team, classification, relevance, fit reason, full-source URL, exact quote and dates. Retain discovery-only evidence and state why it does not qualify. Distinguish observed facts from proposed uses of the offer.
