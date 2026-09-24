# Setup questions

Use [prospect-setup](../workflows/knowledge/prospect-setup.md) to conduct this
interview. Read supplied materials first, ask only for missing or conflicting
answers, and show proposed interpretations. Users need not write JSON. For an
existing configuration, start with its current values and requested changes.

| Topic | Questions to resolve | Owner |
|---|---|---|
| Company and offer | What do you sell, for whom, and what buyer work does it support? Which product names and positioning are approved? | ICP prose for context; claims for assertions |
| Business modules | Does account-based B2B prospecting fit? Select the core for products/services. Enable adoption only for individual/organization subscriptions and ARR growth only for compatible recurring-revenue data. Otherwise leave both disabled. | policy.adoption.enabled, arr_growth.enabled; installation module table |
| Target companies | Which industries, employee range, geography and buying entities fit? What is explicitly excluded or recoverable? | icp.md |
| Buyers | Which roles own the work and decision? What responsibility, problem and desired outcome does each have? | icp.md persona_cares |
| Supported value | Which capabilities or outcomes can you substantiate? Supply exact evidence, scope, limitations and customer proof permissions. Distinguish capabilities, reported examples, inferences and evaluation advice. | claims.json |
| Buying signals | What observable events make the work relevant? What work could each create, which claim answers it, and how fresh must evidence be? Which titles and search queries help find it? | taxonomy.json |
| Voice | Supply an approved or user-authored sample email. What greeting, closing, word limit and language preferences apply? May it be retained privately? | policy.email_voice, outreach.lint; adapters.md retention |
| Operating rules | Who owns the workspace, in which timezone and internal domains? What cadence, suppression, recipient sources and warn/block fit behavior apply? | policy.identity, outreach, followup_signal |
| Source maintenance | Use an existing versioned source or snapshot supplied materials? Where will the private source remain available for refresh? | policy.refresh, claims provenance; adapters.md |
| Optional providers | Which CRM/mail/calendar tools are available, with what native fields, task status/subtype mappings, complete-read and readback rules? Are the selected optional modules authorized and supported? | adapters.md; policy.outreach.task_status_map and enabled capabilities |

Messaging setup can finish before provider setup. Unanswered source/voice
questions remain gaps; do not invent claims or retain synthetic starter messaging.
Present the signal mappings and sample emails for review.
