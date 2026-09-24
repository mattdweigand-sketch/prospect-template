# Optional host entrypoints

All hosts use the same [runtime contract](installation.md), AGENTS.md and
canonical workflows. These thin entrypoints are conveniences, not dependencies
of the workflow engine. No host-specific instructions override a workflow.

| Host convention | Optional entrypoint |
|---|---|
| Codex-compatible skill discovery | .agents/skills/NAME/SKILL.md |
| Claude command discovery | .claude/commands/NAME.md |
| Perplexity Computer or another file-backed agent workspace | If saved instructions and workspace files are available, use the matching thin pointer and preserve all referenced relative paths |
| Any other harness | Read AGENTS.md and CONTEXT.md, then open the selected canonical workflow directly |

Verify the host can resolve the installed files, run the helpers and show exact
review artifacts with a synthetic local run. Do not assume automatic discovery,
file persistence, connector access or successful synchronization. If a host
lacks a required capability, report that workflow unavailable there.

Generate pointers through scripts/wrappers.py; never copy a full procedure into
a host's saved command. Keep private deployment configuration and run artifacts
separate from the public template regardless of host storage conventions.
