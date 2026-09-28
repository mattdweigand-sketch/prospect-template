# Prospect template

Research accounts, check the evidence, prepare a reviewed outreach draft, and log a proven send. This is a native Codex repository with eight small skill entry points. CRM writes and email drafts require review of their exact fields. You send email yourself.

Start with **prospect-setup**. Codex reads your existing materials, asks for missing details, and prepares a configuration for review. You do not need to write YAML or build claim IDs. The checked-in examples are fictional; no live seller identity, provider connection, or customer data is installed.

## Open and set up

1. Open this repository as a Codex project. The root `AGENTS.md` routes requests automatically.
2. Install the local Python dependency from a terminal in this folder:
   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python -m unittest discover -s tests
   ```
   Use Python 3.9 or newer. In Codex, use `.venv/bin/python` for the documented Python commands if the shell has not activated this environment.
3. Type `/`, find **prospect-setup**, and select it in the Codex app's skill menu. Direct skill invocation is `$prospect-setup`; the CLI also exposes skills through `/skills`. The repo's `.agents/skills/` directory supplies discovery. Reopen the project/chat if newly added skills are not listed.
4. Supply a local knowledge repo or product/service documents, your target customers, and a writing sample. Codex prepares the interview, source references, three synthetic examples, and an exact configuration review. Approve that review when it reflects your business.
5. Connect the providers needed for your chosen workflow and complete their field mappings. Setup can finish before all providers are available. Adoption and ARR workflows are off by default and require reviewed warehouse queries.

Native skill discovery is described in the [Codex skills guide](https://learn.chatgpt.com/docs/build-skills) and [app slash-command reference](https://learn.chatgpt.com/docs/reference/slash-commands). A selected skill loads the repository's canonical procedure; it is not a separate copy of the workflow.

## Choose a workflow

| Skill | Use it for |
|---|---|
| `prospect-setup` | Configure or update the business, ICP, messaging, voice and providers |
| `signal-refresh` | Compare a new source revision and stage a reviewed messaging update |
| `signal-prospector` | Discover accounts and propose eligible CRM claims |
| `signal-scan` | Research public buying signals for a named account |
| `signal-user-scan` | Read permitted account-level product adoption, when enabled |
| `signal-outreach` | Turn a qualified bundle into one approved email draft |
| `signal-followup` | Turn proof of a sent message into one approved Task |
| `signal-arr-growth` | Prepare fixed-template drafts for eligible growing self-serve accounts |

The starter content is fictional and offer-neutral. Setup defines the user's company, product or service, ICP, responsibilities, buying signals, supported claims, voice, territory and operating values. Public evidence is judged against that configured offer; internal and customer-facing initiatives can both qualify. Subscription adoption and ARR are optional modules, disabled by default.

CRM and email providers are configurable. Setup maps your available tools, record fields, status values and read/write capabilities to common workflow contracts. IDs and query plans are provider-neutral. A connector still needs verified mappings and complete native readback; this template does not bundle a production adapter for every system.

## Repository map

```text
prospect-template/
├── AGENTS.md                         # Routes requests to workflows
├── CONTEXT.md                        # Handoffs, approvals and storage rules
│
├── .agents/
│   └── skills/                       # Eight small workflow entry points
│
├── workflows/
│   ├── prospect-setup/
│   ├── signal-refresh/
│   ├── signal-prospector/
│   ├── signal-scan/
│   ├── signal-user-scan/
│   ├── signal-outreach/
│   ├── signal-followup/
│   └── signal-arr-growth/
│
├── setup/                            # Onboarding and provider guides
│   ├── CONTEXT.md
│   ├── installation.md
│   ├── questionnaire.md
│   ├── providers.md
│   ├── source-format.md
│   └── subscription-interface.md
│
├── examples/
│   └── config/                       # Fictional starter configuration
│       ├── policy.yaml
│       ├── icp.md
│       ├── signals.md
│       ├── talk-track.md
│       ├── voice.md
│       ├── providers.yaml
│       └── sources.json
│
├── _shared/
│   ├── CONTEXT.md
│   └── scripts/                      # Shared gates and provider mapping
│
├── scripts/                          # Setup, refresh, preflight and maintenance
│
├── _templates/
│   └── workflow/                     # Starter files for a new workflow
│       ├── CONTEXT.md
│       └── procedure.md
│
├── tests/                            # Synthetic workflow and setup tests
├── .github/
│   └── workflows/
│       └── checks.yml                # Python 3.9 and 3.13 CI
│
├── docs/
│   └── BUILD-REPORT.md
│
├── .local/                           # Created as needed; ignored by Git
│   ├── config/                       # Installed business and provider settings
│   ├── setup/                        # Proposals, reviews and receipts
│   ├── sources/                      # Permitted source snapshots
│   └── queries/                      # Reviewed private warehouse queries
│
├── README.md
├── requirements.txt
├── .gitignore
└── LICENSE
```

Each folder under `workflows/` contains a `CONTEXT.md` contract and a `procedure.md`.
Workflow-specific Python checks and SQL files sit beside those instructions.
The corresponding entry in `.agents/skills/` contains a small `SKILL.md` pointer.

Start with [setup](setup/installation.md). [Provider contracts](setup/providers.md)
explain how CRM and email connect. Operational results live in chat and native
provider records; temporary customer files stay outside the checkout.

## Maintenance

Keep values in the installed configuration, workflow steps in one procedure, and skills as pointers. Update configuration through setup/refresh so review receipts remain current. Run `python3 -m unittest discover -s tests` and `python3 scripts/check_repo.py` after repository changes. The tests use synthetic data and simulated provider packets; they do not prove production schema compatibility, live permissions, source truth, consent or delivery.
