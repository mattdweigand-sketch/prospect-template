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

| Path | Purpose |
|---|---|
| `AGENTS.md`, `CONTEXT.md` | Routing, handoffs and state boundaries |
| `.agents/skills/` | Eight short command pointers |
| `workflows/` | Eight contracts and procedures; six operational gates/query interfaces |
| `setup/` | Interview, installation, providers and source evidence format |
| `examples/config/` | Fictional configuration used only for learning and tests |
| `.local/` (ignored) | Installed config, setup reviews, permitted snapshots and private query copies |
| `_shared/scripts/`, `scripts/` | Shared gates and local setup/refresh tools |
| `tests/`, `.github/workflows/checks.yml` | Local behavioral checks and CI definition |
| `docs/BUILD-REPORT.md` | Rebuild provenance, verification and limits |

Operational outputs live in the chat, your email provider and CRM. Temporary customer files stay outside the checkout. There is no send tool, automatic provider setup, scheduled runner, or provider credential bundled here. See [installation](setup/installation.md) and [provider contracts](setup/providers.md) for the concrete steps.

## Maintenance

Keep values in the installed configuration, workflow steps in one procedure, and skills as pointers. Update configuration through setup/refresh so review receipts remain current. Run `python3 -m unittest discover -s tests` and `python3 scripts/check_repo.py` after repository changes. The tests use synthetic data and simulated provider packets; they do not prove production schema compatibility, live permissions, source truth, consent or delivery.
