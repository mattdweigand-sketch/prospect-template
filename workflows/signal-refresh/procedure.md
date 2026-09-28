---
workflow: signal-refresh
reads: active configuration and pinned old/new source commits
writes: local staged setup review; active configuration only after exact approval
next: prospect-setup prepare/apply lifecycle
---

# signal-refresh

Refresh readable ICP, signals, messaging or voice from reviewed source changes. Read `setup/installation.md`, `setup/source-format.md`, and the complete `workflows/prospect-setup/procedure.md`. This workflow never contacts prospects or writes to the source repository.

## Steps

1. Load active sources.json and approval.json. Preserve the baseline revision and actual applied configuration. Inspect a new full source commit; do not use mutable working-tree files or silently follow a branch tip.
2. Run `python3 scripts/refresh_sources.py --revision <full-commit>`. Review every changed, missing or nonregular watched file and any configured contradiction register. Inspect related new source files for missing watch coverage. A no-change result covers watched bytes only; it does not establish continued truth.
3. For a same-repository update, run the command with `--stage-run <new-run-id>`. For newly supplied materials, use `scripts/source_snapshot.py` with the previous snapshot and a new destination, then initialize a setup update and compare committed old/new watch files explicitly. Record both revisions and all affected claims in the staged review context.
4. Update only affected configuration plus necessary watch coverage, preserving unrelated settings. Remove unsupported claims, retain source attribution and limits, and update exact quotes. Source deletion, contradiction or retirement requires meaning review; do not patch wording merely to satisfy quote matching. Review dates may advance only after actual review.
5. Refresh the three synthetic previews and record actual meaning review. Follow the setup procedure's validation, prepare, exact user approval and apply steps. No automatic application, including an unchanged wording/date-only update. Re-run preflight for the next requested workflow.

## Output and stop conditions

Report old/new revisions, changed/deleted watch files, affected wording and retained limits, review location and whether it was applied. Missing source access, unexplained contradictions, incomplete evidence or missing user approval stops the dependent step. Watch coverage is a human responsibility; a hash or passing test never certifies source truth.
