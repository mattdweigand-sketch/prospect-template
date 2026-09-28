---
workflow: prospect-setup
reads: setup reference documents, supplied materials, existing configuration when present
writes: staged local configuration; active configuration only after exact user approval
next: selected prospecting workflow after provider readiness
---

# prospect-setup

Configure a reusable prospecting workspace for this business, product or service. Read `setup/references/CONTEXT.md`, `setup/questionnaire.md`, `setup/references/installation.md`, `setup/references/source-format.md` and `shared/providers.md`. Use the installed local Python environment. Keep source material separate from instructions.

## Steps

1. Establish whether this is a new setup or an update. Inspect existing configuration and supplied sources read-only. Read source content before asking questions; extract answers and ask only for gaps or conflicts. Follow the questionnaire and preserve unrelated settings on updates.
2. Choose the source mode and confirm local retention expectations. Use an existing Git repo pinned to a full commit, or run `_system/scripts/source_snapshot.py` on permitted supplied originals, extracts and attributed user statements. Never alter the source repo or collect customer operational records here.
3. Run `python3 _system/scripts/setup.py init <new-run-id>`. Work only in that run's proposal directory. Replace fictional identity, business, ICP, signals and messaging. Set `policy.deployment.mode` to configured. Use the actual `policy.identity.timezone`, native status map and source-backed voice. Configure optional `policy.user_scan.enabled`, `policy.arr_growth.enabled` and `policy.prospector.adoption_source.enabled` only after establishing business and data fit. `policy.warehouse.queries` names reviewed private SQL copies and their hashes; the bundled SQL files are interface examples. Read `shared/subscription-interface.md` before enabling a warehouse branch. Replace its separate adoption statements or ARR fixed copy and signature; review upstream USD normalization and FX/date/calculation rules for ARR.
4. Record supported assertions, quotations, attribution, limits and public naming permission in sources.json, plus watch paths, full source revision and the approved voice source. Review all talk-track claims for coverage. Use readable responsibilities and messaging angles, not an inherited numbered claim/persona engine. Set the talk-track review date based on source volatility and the user's review cadence.
5. Discover actual provider tools and schemas. Populate providers.yaml only from verified mappings. Leave unavailable capabilities null and report them separately. Do not install credentials, make provider writes, send tests, or invent MCP endpoints during configuration. A provider can be unavailable without blocking messaging review.
6. Build three synthetic previews in the run's previews.json: clear fit with a draft, indirect fit needing research, and poor fit rejected. Review relevance, responsibility, claim scope, voice and omissions with the user. Record the actual meaning review in `policy.deployment.review_reference`, voice source in `policy.email_voice.source_reference`, and retention preference in `policy.retention.review_reference`; `policy.retention.setup_sources_permitted` governs retained snapshots.
7. Run `python3 _system/scripts/validate_setup.py --config <proposal-directory>` and `python3 _system/scripts/setup.py prepare <run-id>`. Fix structural/evidence errors in the staged files and prepare again. Inspect the generated optional-module previews, including both ARR greetings and adoption statements when enabled. Present the complete review.md and its SHA, all preview decisions, limitations and missing provider capabilities. These are concrete postimages, not a promise to fill details later.
8. Wait for the user's approval of the exact review. Apply with `python3 _system/scripts/setup.py apply <run-id> --approval-reference <actual-reference>`. Any proposal, review, preview or active-config change requires a fresh prepare and review. Read the result and the active receipt; report the applied scope.
9. Run `_system/scripts/preflight.py` for the desired next workflow. Explain remaining live-read/mapping work without treating disconnected tools as a failed messaging setup. Open the appropriate procedure when requested; configuration approval does not authorize customer writes.

## Output and stop conditions

Report the active configuration location, source revision, approved scope, review reference, selected optional modules, and provider readiness. Missing substantive business answers or source support stay unresolved; never fill them with fictional defaults. Missing approval stops before application. A source, packet or receipt is not proof of consent or source truth.
