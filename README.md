# Prospect Workflow Template

Seven configurable workflows for signal research and reviewed outreach.
Built with the Interpretable Context Methodology: small routing files, explicit
workflow contracts, shared configuration and editable, human-reviewed run outputs.

Start with [setup](setup/CONTEXT.md). Agents enter through [AGENTS.md](AGENTS.md).
This repository is independent of its Sales companion.
Cross-project handoffs pass explicit evidence, never shared mutable local state.

## Workflows
See [the task router](CONTEXT.md) for all seven commands and their canonical owners.

## Structure
- `workflows/`: canonical procedures grouped by task family; run.md owns the common review lifecycle.
- `_shared/`: common boundaries and example configuration; deployment values stay local.
- `_templates/`: copied run starter; products live in ignored output/{run-id}/.
- `.agents/skills/` and `.claude/commands/`: generated thin pointers.
- `scripts/` and `tests/`: local checks, wrapper generation and run-state tooling.

## Validate
```bash
python3 scripts/check_repo.py
python3 -m unittest discover -s tests -v
```

No network services are called by these checks. See [portability](setup/portability.md)
for required adapters and the limits of local validation. The template is not
connected to a CRM, mail account, warehouse or live Perplexity Project.

## Contribute
Edit the owning workflow or factory file, then update the wrapper registry only
if routing changes. Run `python3 scripts/wrappers.py` to regenerate task maps and pointers,
and validate. Keep examples synthetic and never commit deployment configuration
or run outputs. [MIT license](LICENSE).
