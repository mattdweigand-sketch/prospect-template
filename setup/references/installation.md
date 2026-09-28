# Local installation and configuration lifecycle

Use the Python environment described in the README. Commands below run from the repository root; replace `python3` with `.venv/bin/python` when needed. No Codex SDK or custom prompt framework is required. Skills are discovered from `.agents/skills/` in this checkout. Do not install a second global copy unless the user separately requests it.

## Prepare the business configuration

The `prospect-setup` workflow conducts the interview and runs these commands for the user:

```sh
python3 _system/scripts/setup.py init initial-setup
```

This copies fictional examples (or the current installed config for an update) to `.local/setup/initial-setup/proposal/`. It clears the inherited review reference. Edit all relevant postimages there, record source evidence, and fill `previews.json` with `clear_fit`, `indirect_fit`, and `poor_fit` scenarios. Each has `scenario`, `decision` (`draft`, `research`, `reject`), `reason`, and `draft` when relevant. Only synthetic accounts belong in these previews.

```sh
python3 _system/scripts/validate_setup.py --config .local/setup/initial-setup/proposal
python3 _system/scripts/setup.py prepare initial-setup
```

The result is a full `review.md` containing diffs, complete proposed files and previews. For enabled optional modules, it also renders the exact ARR draft with both person and team greetings and includes the adoption statements. Replace all fictional optional-module wording before enabling it; disabled modules may retain scaffolding. Review those samples alongside business meaning, source sufficiency, naming/disclosure permission, voice and operating values. `deployment.review_reference` records that meaning review; it is not approval to apply. Prepare also binds active preimages, proposed bytes, source revision and preview bytes. Present the exact review and its SHA to the user.

After the user's approval of that exact review:

```sh
python3 _system/scripts/setup.py apply initial-setup --approval-reference '<actual chat approval reference>'
```

The command revalidates, checks hashes and expected active preimages, stages the full configuration, applies under an exclusive lock, verifies readback and writes a receipt. An existing configuration is retained at the run's `previous-config/`. Changed proposals or current files require a new prepare and approval. A fabricated reference does not create authorization.

## Configuration contracts

ICP frontmatter requires the employee range, a `verticals` list of unique nonblank IDs with positive integer ranks, and `disqualifiers.hard` / `disqualifiers.recoverable` lists of distinct IDs. Empty lists mean no preference or exclusion in that category. Signals require `tier1`, `tier2` and `tier3` lists, unique IDs, positive freshness days for counted tiers, and a nonblank source reference on warehouse signals. An enabled adoption-discovery signal must name a tier2 warehouse entry.

Follow-up task subjects accept `{email_subject}`. Descriptions accept `{message_id}`, `{thread_id}`, `{signal_type}`, `{angle}` and the legacy alias `{unit}` for the same historical angle. ARR person greetings accept `{first_name}` and team greetings accept `{account_name}`; its subject and body are fixed text with no fields. Templates accept bare named fields only, without format specifiers, conversions or attribute access. Use doubled braces for literal braces in rendered templates. Setup renders representative values with the same helpers as the workflows and rejects unsupported fields.

## Source modes

Use an existing local Git knowledge repo read-only, pinned to a full commit, or take a permitted snapshot of supplied files as described in `source-format.md`. Source snapshots and drafts remain private under `.local/`. Source capture records provenance; it does not bless the content. The setup process never edits the source repo or its working tree.

## Providers and preflight

Complete `providers.yaml` from current tool discovery and real tool schemas. Configuration may be applied with disconnected providers. Before an operational workflow, run for example:

```sh
python3 _system/scripts/preflight.py signal-scan
```

This checks all seven active approval hashes and configuration structure, then the selected workflow's dependencies. New signal outreach checks the current talk-track review date and pinned messaging/voice evidence. Historical follow-up and public research do not require current talk-track content. ARR uses its reviewed fixed copy. Query hashes are checked only for the selected enabled warehouse branch; an unavailable ARR query does not block public scanning. Setup preparation and application still validate all messaging evidence and every enabled query. Preflight also checks module selection and declared capabilities. Then verify actual tool availability and complete authorized live reads. No endpoint, token, scope or capability is inferred from a checked-in mapping. Put credentials in the provider's normal connection mechanism, never a repository file. An optional project `.codex/config.toml` is only added after a real MCP setup is known; this template does not invent one.

The three SQL files are fictional interface examples, not deployed schema. Read `shared/subscription-interface.md` for the public view contract and business-model requirements. For each enabled warehouse branch, create a reviewed private `.local/queries/` copy, map actual tables/columns and semantics, record its SHA in policy, verify parameter binding and allowed result fields, and perform authorized read-only compatibility checks. A schema name replacement alone is insufficient. Data dates follow the configured identity time zone; the source must use the same daily boundary. Existing ARR private mappings must be reviewed for upstream USD normalization and return the explicit `currency: USD` field. Update the query hash through setup and approve the revised review before using that mapping. Packets without the field are rejected.

## Refresh and recovery

```sh
python3 _system/scripts/refresh_sources.py --revision '<full source commit>' --stage-run messaging-refresh
```

Review changed/deleted watched sources and the optional contradiction register, update affected claims and wording, and use the same prepare/apply flow. For new supplied materials, create a new snapshot with `--previous`, then stage a setup update pointing to that snapshot and explicitly compare the old/new committed watch files. Never merely advance the review date.

After interruption, inspect `.local/setup/<run>/review.json`, `applied.json`, active `approval.json` and any `previous-config/` or `failed-config/`. A remaining `.local/apply.lock` may indicate a crash or another apply; establish which before removing it. Do not blindly retry an apply or restore a backup. Compare native/local state and obtain fresh review if uncertain. These records support normal recovery; they are not a tamper-resistant transaction journal or an access-control system.

Private setup sources are not saved by Git. Apply your chosen backup/retention policy. To share the reusable template, export only tracked files; never zip the entire configured directory blindly.
