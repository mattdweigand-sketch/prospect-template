# Prospect Workflow Template

Seven configurable workflows for signal research and reviewed outreach.
Built with the Interpretable Context Methodology: small routing files, explicit
workflow contracts, shared configuration and editable, human-reviewed run outputs.

Start with [setup](setup/CONTEXT.md). Agents enter through [AGENTS.md](AGENTS.md).
Cross-project handoffs pass explicit evidence, never shared mutable local state.

## Workflows

See [the task router](CONTEXT.md) for all seven commands and their canonical owners.

## Structure

- `workflows/`: canonical procedures grouped by task family; run.md owns the common review lifecycle.
- `_shared/`: common boundaries and example configuration; deployment values stay local.
- `_templates/`: copied run starter; products live in ignored output/{run-id}/.
- `.agents/skills/` and `.claude/commands/`: generated thin pointers.
- `scripts/` and `tests/`: evidence and action checks, wrapper generation and run-state tooling.

## Validate

```bash
python3 -B scripts/check_repo.py
python3 -B -m unittest discover -s tests -v
```

These checks use synthetic local inputs. Configure the required adapters through
[installation](setup/installation.md) before using live CRM, mail or warehouse data.
Local tests do not verify provider access or approval of a real action.

## Contribute

Edit the owning workflow or factory file, then update the wrapper registry only
if routing changes. Run `python3 scripts/wrappers.py` to regenerate task maps and pointers,
and validate. Keep examples synthetic and never commit deployment configuration
or run outputs. [MIT license](LICENSE).
