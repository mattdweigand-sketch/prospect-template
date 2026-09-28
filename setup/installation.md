# Local installation and configuration lifecycle

Use the Python environment described in the README. Commands below run from the repository root; replace `python3` with `.venv/bin/python` when needed. No Codex SDK or custom prompt framework is required. Skills are discovered from `.agents/skills/` in this checkout. Do not install a second global copy unless the user separately requests it.

## Prepare the business configuration

The `prospect-setup` workflow conducts the interview and runs these commands for the user:

```sh
python3 scripts/setup.py init initial-setup
```

This copies fictional examples (or the current installed config for an update) to `.local/setup/initial-setup/proposal/`. It clears the inherited review reference. Edit all relevant postimages there, record source evidence, and fill `previews.json` with `clear_fit`, `indirect_fit`, and `poor_fit` scenarios. Each has `scenario`, `decision` (`draft`, `research`, `reject`), `reason`, and `draft` when relevant. Only synthetic accounts belong in these previews.

```sh
python3 scripts/validate_setup.py --config .local/setup/initial-setup/proposal
python3 scripts/setup.py prepare initial-setup
```

The result is a full `review.md` containing diffs, complete proposed files and previews. Review business meaning, source sufficiency, naming/disclosure permission, voice and operating values. `deployment.review_reference` records that meaning review; it is not approval to apply. Prepare also binds active preimages, proposed bytes, source revision and preview bytes. Present the exact review and its SHA to the user.

After the user's approval of that exact review:

```sh
python3 scripts/setup.py apply initial-setup --approval-reference '<actual chat approval reference>'
```

The command revalidates, checks hashes and expected active preimages, stages the full configuration, applies under an exclusive lock, verifies readback and writes a receipt. An existing configuration is retained at the run's `previous-config/`. Changed proposals or current files require a new prepare and approval. A fabricated reference does not create authorization.

## Source modes

Use an existing local Git knowledge repo read-only, pinned to a full commit, or take a permitted snapshot of supplied files as described in `source-format.md`. Source snapshots and drafts remain private under `.local/`. Source capture records provenance; it does not bless the content. The setup process never edits the source repo or its working tree.

## Providers and preflight

Complete `providers.yaml` from current tool discovery and real tool schemas. Configuration may be applied with disconnected providers. Before an operational workflow, run for example:

```sh
python3 scripts/preflight.py signal-scan
```

This checks active approval hashes, current source/configuration validity, module selection, and declared capabilities. Then verify actual tool availability and complete authorized live reads. No endpoint, token, scope or capability is inferred from a checked-in mapping. Put credentials in the provider's normal connection mechanism, never a repository file. An optional project `.codex/config.toml` is only added after a real MCP setup is known; this template does not invent one.

The three SQL files are fictional interface examples, not deployed schema. Read `setup/subscription-interface.md` for the public view contract and business-model requirements. For each enabled warehouse branch, create a reviewed private `.local/queries/` copy, map actual tables/columns and semantics, record its SHA in policy, verify parameter binding and allowed result fields, and perform authorized read-only compatibility checks. A schema name replacement alone is insufficient. Data dates follow the configured identity time zone; the source must use the same daily boundary.

## Refresh and recovery

```sh
python3 scripts/refresh_sources.py --revision '<full source commit>' --stage-run messaging-refresh
```

Review changed/deleted watched sources and the optional contradiction register, update affected claims and wording, and use the same prepare/apply flow. For new supplied materials, create a new snapshot with `--previous`, then stage a setup update pointing to that snapshot and explicitly compare the old/new committed watch files. Never merely advance the review date.

After interruption, inspect `.local/setup/<run>/review.json`, `applied.json`, active `approval.json` and any `previous-config/` or `failed-config/`. A remaining `.local/apply.lock` may indicate a crash or another apply; establish which before removing it. Do not blindly retry an apply or restore a backup. Compare native/local state and obtain fresh review if uncertain. These records support normal recovery; they are not a tamper-resistant transaction journal or an access-control system.

Private setup sources are not saved by Git. Apply your chosen backup/retention policy. To share the reusable template, export only tracked files; never zip the entire configured directory blindly.
