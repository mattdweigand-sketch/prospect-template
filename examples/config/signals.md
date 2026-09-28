---
admission:
  tier1_min: 1
  tier2_min: 2
  warehouse_needs_web_tier2: true
  warehouse_max_counted: 1
tiers:
  tier1:
  - id: ai_exec_appointment
    freshness_days: 90
  - id: public_ai_initiative
    freshness_days: 60
  - id: ai_rfp_or_procurement
    freshness_days: 45
  - id: earnings_ai_commitment
    freshness_days: 90
  - id: incumbent_standardization
    freshness_days: 120
  - id: ai_governance_formalization
    freshness_days: 90
  tier2:
  - id: ai_hiring_cluster
    freshness_days: 30
  - id: exec_ai_statements
    freshness_days: 60
  - id: ai_vendor_partnership
    freshness_days: 90
  - id: ai_earmarked_funding
    freshness_days: 120
  - id: paid_individuals_present
    freshness_days: 1
    source: workflows/signal-prospector/adoption_territory.sql
  tier3:
  - id: generic_ai_marketing
  - id: single_job_post
  - id: industry_trend_mention
  - id: discovery_only
---

# Fictional example signals

This fictional AI research example illustrates the workflow. Setup replaces its business choices; it is not approved live configuration.

**Find evidence that a company is planning, funding, hiring for, testing, deploying, or expanding AI.** Search broadly, identify the actual initiative, and connect it to a relevant person and potential Example Research use case.

A signal establishes a reason to investigate. It does not establish pain, available budget, purchase intent, or permission to contact an account.

## Signals to look for

| Signal | Where to look | Evidence to capture |
|---|---|---|
| **Dedicated AI hiring** | Company careers pages and job boards | Roles responsible for AI adoption, enablement, transformation, internal agents, or tool evaluation. One substantive posting can identify an initiative; multiple openings add context. |
| **AI responsibilities in ordinary roles** | Sales, marketing, finance, operations, and HR job descriptions | Responsibility for introducing AI into the team's work, automating a process, or training colleagues. Familiarity with an AI tool alone is a weaker clue. |
| **New AI leadership or team** | Appointment announcements, leadership pages, LinkedIn | An AI leader, transformation office, center of excellence, or implementation team with a stated mandate. |
| **Announced AI initiatives** | Press releases, company blogs, strategy updates | Programs, pilots, tool evaluations, standardization, or rollouts. Capture any named team, owner, workflow, investment, partner, or timeline; a stated budget is not required. |
| **Executive commitments** | Earnings calls, investor presentations, annual reports, interviews | Plans to invest in AI, change workflows, improve productivity, or expand adoption. Retain specific intent even when tools and workflows are not yet disclosed. |
| **Employee and leader posts** | Public LinkedIn posts, conference talks, podcasts | Firsthand accounts of implementing tools, running pilots, building workflows, or training colleagues. Record the speaker's role and the scope they actually describe. |
| **Training and adoption programs** | Company posts, events, careers pages | AI academies, training cohorts, champion networks, workshops, hackathons, or adoption targets connected to company work. |
| **Vendor and consulting engagements** | Customer stories, partner announcements, implementation case studies | A named company evaluating or implementing AI with a vendor or services partner. Identify the project scope and distinguish implementation from resale or distribution. |
| **Procurement and budget activity** | RFPs, RFIs, procurement portals, public budgets | Funding or evaluation of AI assistants, enterprise search, knowledge tools, agents, or implementation services. Capture requirements, deadlines, and the responsible team. |
| **Internal technical investment** | Engineering blogs, technical talks, job descriptions | Internal assistants, enterprise search, knowledge retrieval, AI integrations, or shared model infrastructure connected to actual company work. |
| **Governance and organizational readiness** | Company policies, committee announcements, governance hiring | Establishing approved tools, employee-use policies, review processes, or ownership for AI adoption. Governance activity alone does not establish a purchase. |
| **Expansion, results, or implementation problems** | Earnings updates, customer stories, executive posts | Moving beyond a pilot, adding departments, reporting adoption, or discussing specific cost, quality, integration, or adoption challenges. Preserve the company's attribution for claimed results. |

Search both company sources and relevant public reporting. AI references in careers pages, press releases, and earnings materials are worth inspecting even when the headline does not announce an AI program.

## Interpret the evidence

| Classification | Meaning | Example |
|---|---|---|
| **Active initiative** | Concrete evidence of current funding, hiring for delivery, evaluation, implementation, or expansion. State the actual stage. | A role tasked with delivering the company's AI adoption plan; a department testing an assistant. |
| **Early indication** | Specific interest or intent; execution is unclear. | A CFO announces plans to invest in AI productivity without describing an implementation. |
| **General mention** | AI commentary or marketing without an identifiable company action. | “AI is transforming our industry”; a job requiring familiarity with ChatGPT. |

Judge the substance, not the number of mentions. **One detailed job posting can establish hiring for an initiative.** It does not establish that the initiative is already deployed. A cluster of vague postings does not fix missing substance.

Search snippets help locate evidence; read the full source before classifying it. Attribute employee observations and vendor claims to their speakers rather than treating them as company-wide commitments.

## Identify Example Research relevance

Capture customer-facing initiatives as well as internal ones. Label each finding:

- **Employee use:** AI for research, analysis, company knowledge, documents, reporting, or operational workflows. Find the initiative owner or affected team leader.
- **Customer-facing product/API:** AI embedded in the company's product or customer experience. Find the product or technical owner and assess the research/API opportunity separately.
- **Unclear:** AI activity is evident, but its users or purpose need further research.

A company selling AI may also adopt AI internally; establish each separately. An incumbent rollout does not imply dissatisfaction. Ordinary funding, acquisitions, or expansion provide context unless the evidence explicitly connects them to an AI initiative.

## Check whether the initiative is current

Record the source date and when it was checked. Verify whether the job remains open, the procurement window remains active, or the program is still being implemented or expanded. An older announcement can remain relevant when current evidence supports it. Mark missing dates or unresolved status as unknown; do not invent recency.

Count one underlying initiative once, even when several outlets or posts cover it. Preserve updates that show a change in its stage or scope.

## Verified Example Research adoption and spend

These require authorized, privacy-checked warehouse results; public mentions cannot substitute for the account-level checks.

| Result | Meaning and use |
|---|---|
| **Paid individual adoption** | Paid individuals are present and no organizational subscription is mapped to the account. Use the prior completed daily snapshot, within **1 day**. Permitted statement: **“People at the organization already pay for Example Research individually.”** |
| **Organizational adoption** | Permitted statement: **“Example Research is already adopted at the organization.”** Adds context; it does not independently establish an outreach opportunity. |
| **Growing organizational self-serve spend** | Verified positive growth over **30 days**, with complete daily coverage. Use the separate spend-growth workflow, billing contact, and fixed approved email. |
| **No adoption found** | Make no adoption claim. An empty result is not proof of absence; account mapping may be incomplete. |

Do not infer a champion's identity, personal payment, unsanctioned use, or company disapproval. Never expose individual adoption identities, user emails, user or seat counts, queries, or usage timing. Spend figures stay out of prospect messages.

## Record and use findings

Keep **account · initiative and stage · owner or team · evidence classification · source URL, supporting quote, and dates · Example Research relevance**. Mark unknowns explicitly and separate observed facts from proposed use cases.

Retain useful discovery evidence even when it does not meet an automated qualification threshold. These classifications do not override the live workflows' qualification, freshness, ownership, open-Opportunity, recent-contact, or approval checks. Discovery and permission to act remain separate.

## Qualification for automated workflows

The search categories above describe what to investigate. The identifiers below preserve the existing automated qualification rules. They are not persona or messaging mappings. Use `discovery_only` for useful findings that do not meet one of these definitions. Early indications, general mentions, customer-facing/API initiatives, and unclear relevance remain reportable but do not enter the employee-outreach or claim handoff. A single substantive job can prove an active initiative while remaining discovery-only under the current hiring threshold.

For an employee-use finding, select a qualifying identifier only when the source meets its definition, then apply the frontmatter freshness window. Classification and relevance belong to each finding, not to its search category.

| Identifier | Evidence required in addition to active initiative and employee use |
|---|---|
| `ai_exec_appointment` | A named executive appointment with AI in the mandate (Chief AI Officer, VP/Head of AI, Head of GenAI programs) announced by the company or credible press. |
| `public_ai_initiative` | A company-announced AI program with at least one concrete element: budget, timeline, named workflow, or named business unit. |
| `ai_rfp_or_procurement` | A public RFP, RFI, or procurement notice for AI tooling, enterprise search, or research/knowledge tooling. |
| `earnings_ai_commitment` | An earnings-call or investor-day commitment to deploy AI in a named internal workflow (not product roadmap AI features). |
| `incumbent_standardization` | An announced or reported standardization on an AI tool for employees. Do not infer dissatisfaction or gaps. |
| `ai_governance_formalization` | A published AI usage policy, governance committee, or responsible-AI framework, signaling the company is moving from ad hoc AI use to sanctioned tooling. |
| `ai_hiring_cluster` | Two or more simultaneously open AI-adjacent roles (AI enablement, prompt engineering, AI program manager, ML platform) at one company. |
| `exec_ai_statements` | A named executive publicly discussing evaluating or adopting AI tooling (interview, keynote, podcast, LinkedIn), specific enough to name a problem or workflow. |
| `ai_vendor_partnership` | An announced partnership or pilot with an AI vendor or systems integrator for internal use cases. |
| `ai_earmarked_funding` | A funding round, budget line, or capital allocation explicitly earmarked for AI capability building. |
| `paid_individuals_present` | The privacy-checked warehouse result described above; never a public-web substitute. |

Tier 3 identifiers (`generic_ai_marketing`, `single_job_post`, `industry_trend_mention`, `discovery_only`) never qualify. For new-account claims, the frontmatter admission thresholds and warehouse pairing still apply; a named-account scan uses its existing one-qualified-signal rule. Neither verdict is approval to write.
