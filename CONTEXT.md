# Task router

Generated from scripts/wrapper-contract.json. Do not hand-edit this task map.

Select one task. Open its family CONTEXT.md, then the matching canonical workflow.
Do not load the other families.

| Task / command | Workspace | Purpose |
|---|---|---|
| `signal-scan` | [research](workflows/research/CONTEXT.md) | Find and qualify public buying signals for one named account. |
| `signal-user-scan` | [research](workflows/research/CONTEXT.md) | Produce an organization-level adoption finding using a configured private-data adapter. |
| `signal-prospector` | [research](workflows/research/CONTEXT.md) | Discover candidate accounts, resolve CRM ownership, and propose exact account claims. |
| `signal-outreach` | [outreach](workflows/outreach/CONTEXT.md) | Prepare one evidence-backed cold email and create an unsent draft after exact approval. |
| `signal-followup` | [outreach](workflows/outreach/CONTEXT.md) | Create one CRM follow-up task after a uniquely identified email was actually sent. |
| `signal-arr-growth` | [outreach](workflows/outreach/CONTEXT.md) | Find eligible self-service growth accounts through a configured billing adapter and propose template drafts. |
| `signal-refresh` | [knowledge](workflows/knowledge/CONTEXT.md) | Propose claim-library updates from a configured, versioned knowledge source. |

Setup: [setup/CONTEXT.md](setup/CONTEXT.md). Run state: [workflows/run.md](workflows/run.md).
