# Prospect Workflow Template

Harness-independent B2B prospecting for products and services: guided setup,
five core workflows, and two optional subscription-business workflows.
Built with the Interpretable Context Methodology: small routing files, explicit
workflow contracts, shared configuration and editable, human-reviewed run outputs.

Start with [setup](setup/CONTEXT.md). Agents enter through [AGENTS.md](AGENTS.md).
Cross-project handoffs pass explicit evidence, never shared mutable local state.
The core requires no model-provider SDK or vendor-specific agent API. Any harness
that meets the [runtime contract](setup/installation.md) can read the same
workflows and execute their checks. Host shortcuts are optional.

Say **run setup** to install your own ICP, messaging, buying signals and email
voice. Supply existing materials or answer a guided interview. Review the
signal-to-value-proposition mappings and sample emails before installation.
CRM/mail configuration can follow separately. Say `prospect-setup` to update
an existing configuration without resetting unrelated settings.

## Workflows

See [the task router](CONTEXT.md) for setup and the seven operating commands.
The core covers public signals, account discovery, outreach, follow-up and
claim refresh. Organization adoption and ARR growth are optional modules;
setup leaves them disabled unless their business model and data contracts fit.
The current operational model uses business accounts, contacts and CRM ownership.
Consumer prospecting and outreach without a CRM need separate workflow support.

## Structure

- `workflows/`: canonical procedures grouped by task family; run.md owns the common review lifecycle.
- `_shared/`: common boundaries and example configuration; deployment values stay local.
- `_templates/`: copied run starter; products live in ignored output/{run-id}/.
- `.agents/skills/` and `.claude/commands/`: optional generated host entrypoints; the workflows remain canonical.
- `scripts/` and `tests/`: evidence and action checks, wrapper generation and run-state tooling.

## Validate

```bash
python3 -B scripts/check_repo.py
python3 -B -m unittest discover -s tests -v
```

These checks use synthetic local inputs. Configure the required adapters through
[installation](setup/installation.md) before using live CRM, mail or warehouse data.
Local tests do not verify provider access or approval of a real action.
Check your installed messaging with `python3 scripts/validate_setup.py --source SOURCE_CLONE`;
this reports evidence/configuration readiness separately from provider verification.

## Contribute

Edit the owning workflow or factory file, then update the wrapper registry only
if routing changes. Run `python3 scripts/wrappers.py` to regenerate task maps and pointers,
and validate. Keep examples synthetic and never commit deployment configuration
or run outputs. [MIT license](LICENSE).
