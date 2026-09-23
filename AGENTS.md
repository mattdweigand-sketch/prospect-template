# Prospect Workflow Template

A configurable, human-reviewed prospecting workspace.
This is the canonical agent entry. CLAUDE.md and generated skills point here.

Read [CONTEXT.md](CONTEXT.md), choose one task, then open its workspace contract.

| Need | Owner |
|---|---|
| Run a workflow | [Task router](CONTEXT.md) |
| Configure a new deployment | [Setup](setup/CONTEXT.md) |
| Find shared rules and settings | [Factory](_shared/CONTEXT.md) |
| Start, resume or inspect a run | [Run contract](workflows/run.md) |
| Change tools or regenerate wrappers | [Tooling](scripts/CONTEXT.md) |
| Find blank run starters | [Templates](_templates/CONTEXT.md) |
| See a synthetic review | [Examples](examples/CONTEXT.md) |

All paths are repository-relative. Read the selected workflow's Load / Skip
list before retrieving customer context. Installation guidance lives in
[setup/installation.md](setup/installation.md).
