# Prospect audit remediation spec

Status: implemented and independently verified on 2026-09-23. See section 8 for completion evidence.
Baseline: `901b31593b5a33e62afca996be6e9f4cb57c3f52`, 90 files, 241 passing tests.
Purpose: close every finding from the full-repository audit with small, reviewable changes.
This is a maintenance document, not an input to prospecting runs.

## 1. Design decisions

- Keep the existing folders, eight workflows, Python standard library, JSON factory, generated wrappers and two-stage run lifecycle.
- Fix local defects locally. Reuse a few validation functions only where multiple callers need the same rule.
- Keep chosen values in the factory, fixed checks in Python, and source meaning, fit, voice and actual approval with people.
- Add one small run-input manifest and a fixed preflight over existing helpers. Do not add a workflow framework, schema language, plugin system, database, background service or action executor.
- Preserve useful partial findings. A blocked effect does not make the entire research report unusable.
- Keep provider truth and authorization distinct from local validation. No new check can certify that a conversation reference is consent or that an adapter really completed its reads.
- Use file-level dependency scoping first. Do not introduce field-selector expressions or fine-grained policy hashing.
- Do not rewrite healthy modules, delete workflow families, or remove meaningful tests to reduce line count.

## 2. Scope and traceability

IDs below cover all main findings, smaller defects and structural observations in the audit. Each row is mandatory; the implementation may combine related changes.

| ID | Finding | Implementation owner | Required regression or acceptance case |
|---|---|---|---|
| A01 | Ready runs need not contain required inputs or passing checks | `runs.py`, new `run_checks.py`, run template/contract | Empty-artifact outreach cannot become an effect-ready review; blocked research remains reviewable; evidence handoffs are checked |
| A02 | Malformed nested records pass gates | Existing gate modules; shared primitives in `factory.py` | Empty task objects, null IDs, wrong collection types and malformed addresses never produce eligible effects |
| A03 | Internal domains bypass routing exclusion | `factory.py`, `route_candidate.py` | Trailing-dot internal host is excluded; control whitespace is rejected |
| A04 | Setup passes unusable configuration | `factory.py`, `validate_setup.py` | Missing lint fields or the scan section produce actionable configuration errors, not a pass followed by a crash |
| A05 | Refresh drops deletions and misses accepted path forms | `refresh_tracks.py` | Deletion, nested watch directory, normalized source root, rename-as-delete/add and directory-prefix collision cases |
| A06 | Title substrings admit unrelated roles | `outreach_gate.py` | Payroll/Procurement Coordinator does not match COO; a legitimate extended title still matches |
| A07 | Subject bypasses email restrictions | `outreach_gate.py`, `lint_draft.py` | Unsupported subject numbers, forbidden proof names and formatting are rejected |
| A08 | Shared proof names falsely block approved claims | `outreach_gate.py` | A permitted selected proof remains usable when another row names the same customer |
| A09 | Negative/unknown adoption categories authorize statements | `outreach_gate.py`, configuration validation | Both categories block sentences even when configuration includes matching text |
| A10 | Verdict accepts invalid envelopes/dates or crashes | `scan_verdict.py` | Invalid/noncanonical dates, emoji dates, unknown outcomes and non-object records return structured errors |
| A11 | Worktrees evade tracked-private-file checks | `check_repo.py` | Main checkout and linked worktree both reject the same tracked private file |
| A12 | ARR tie-breaker is unenforced | `arr_growth_gate.py` | Equal-growth rows use account-ID order before the cap |
| A13 | ARR literal prohibition is case-sensitive | `arr_growth_gate.py` | ARR in mixed/lower case and the explicit expanded phrase are rejected |
| A14 | Common Markdown/emoji forms evade lint | `lint_draft.py` | Links, blockquotes, underscore emphasis, backticks and flag emoji are detected without rejecting plain URLs |
| A15 | Configurable-looking policy has independent code/prose owners | Policy example, routing helper and workflow references | Fixed admission behavior has one owner; stale settings cannot silently suggest another behavior |
| A16 | Test-only production functions duplicate real logic | `refresh_tracks.py`, its tests | Production committed-blob report covers whitespace/case behavior; remove unused duplicate helpers |
| A17 | Setup loads too much at once | Setup workflow, questionnaire, installation and helper help text | Each setup phase names narrow inputs; ordinary setup no longer requires reading helper implementations |
| A18 | Unrelated factory changes invalidate reviews | Wrapper registry, `runs.py`, tests | Claims changes leave a scan review current; relevant taxonomy changes invalidate it |
| A19 | Warm-engagement retrieval can be shorter than evaluation window | Scan workflow, existing routing helper, configuration validation | A qualifying task between the two windows is retrieved and stops an actionable handoff |

## 3. Input and configuration validation

### 3.1 Shared primitives, not a schema framework

Add small functions to [factory.py](scripts/factory.py) for nonblank strings/IDs, string lists, normalized domains and supported single email addresses. Keep record-specific shape validation inside the gate that owns that record. Error messages identify the field and expected shape.

Domain handling: lowercase; normalize an optional terminal DNS dot; reject whitespace/control characters, URLs, ports, paths, empty labels and invalid DNS labels. Normalize configured internal domains through the same function. Use standard-library IDNA conversion for international domain names. Compare canonical hosts and subdomain boundaries; do not perform DNS lookups or infer buying-entity relationships.

Email handling: accept one supported unquoted address, with a valid dot-atom local part and validated domain. Reject address lists, display-name syntax, commas, semicolons, controls and leading/trailing/consecutive local-part dots. Preserve the exact reviewed recipient in the proposed payload; normalization is for validation/comparison, not silent editing. Unsupported address syntax produces an explicit input error. Syntax validation does not establish deliverability or consent.

Use the same address validation in setup, outreach, follow-up and ARR. Do not generalize into a full RFC email parser.

### 3.2 Required gate shapes

Before business rules run, validate the fields actually used by that gate, including their nested types:

- **Routing:** existing-account owner ID is a nonblank string; owner activity is a real boolean; new-account owner fields are null; opportunity IDs are nonblank strings in a list. Reject contradictory new-account/open-opportunity inputs. Signal records contain known IDs and matching tiers. Preserve null headcount as an explicit unknown that cannot be claimed.
- **Follow-up:** account/contact/message/thread IDs are nonblank strings; the contact belongs to the non-null account; recipient addresses validate; contacts and tasks are lists of objects. Every task supplies ID, subject, status and description, with description permitted to be an empty string. Missing duplicate-check fields are unusable input, not empty activity. An unfamiliar nonblank status remains conservatively open unless explicitly closed by policy. Exactly one matching contact remains required.
- **ARR:** eligible organization/account/contact IDs are nonblank strings; contacts is a list, never a string/object; a no-contact result is exactly `[]`. Explicitly unresolved candidates may have null mapping IDs only when mapping is unverified or no CRM account exists; hold them and exclude unresolved IDs from duplicate/tie comparisons. Wrong value/container types remain input errors. Account fields and headcount source are present, with unknown headcount represented explicitly and held. Validate dates, numbers and collections before duplicate counting or ranking. Preserve existing holds for mapping ambiguity, coverage, permission, ownership, territory and suppression.
- **Outreach:** validate bundle, claim, recipient, activity and draft containers and consumed fields before using string/dictionary methods. Empty lists are valid only where the contract permits them. Receipt completeness remains supported by references and human/provider review.

Malformed input returns structured JSON and the helper's documented unusable-input exit code. A structurally valid but ineligible record remains a held/blocked business result. Update tests that currently treat missing task fields as a complete read; do not add artificial defaults in fixtures to conceal missing provider mappings.

### 3.3 Validate configuration at its consumption boundary

Centralize reusable policy-section validation in `factory.py`; each operating helper requests only the sections it consumes. Put validation on the callable check/load path, not just in CLI `main()`, so preflight's direct calls receive the same checks and structured failures. `validate_setup.py` applies the complete core configuration checks and the checks for enabled optional modules. Existing valid example configurations remain usable for synthetic work.

Cover every consumed setting: required keys; actual booleans; integer counts/windows with appropriate bounds; timezone; lists/maps; known enums; fit mode; recipient sources; suppression subtypes; all lint keys; scan limits and warm-engagement settings; routing IDs; prospector limits; follow-up cadence/statuses/template fields; refresh paths/cap; and enabled optional-module settings. Missing fields and invalid types report their paths. Use the existing example shapes as the reference, not a second JSON-schema file.

Messaging setup may still finish with provider mappings explicitly unconfigured. An empty status map is allowed at that stage; operating gates continue to reject actual unmapped task statuses. Disabled optional modules do not require live adapters or an ARR email template.

Validate format-string placeholders against each template's supported names before use. Reject adoption statement keys outside `org_adopted` and `individuals_only`. Preserve the distinction between configuration validity, messaging readiness and provider readiness.

For warm engagement, request task history covering `max(outreach.activity_lookback_days, scan.warm_engagement.lookback_days)`. Evaluate the configured scan window separately from outreach suppression. Add a small scan-route function to the existing routing module for open-deal precedence, owner exclusions, other-owner routing and warm-subject matching; call it from preflight. Missing/incomplete CRM data permits a limited public report but no actionable outreach handoff. Do not add a CRM connector.

## 4. Small corrections to existing behavior

### 4.1 Outreach and lint

Use case-insensitive whole-token/phrase matching for configured title aliases. An extended title may contain a complete configured phrase; a fragment of that phrase cannot match in reverse. Keep exact named-executive matching and the existing reasoned override. Do not add title inference, an ontology or fuzzy matching.

Check subject and body for unsupported numbers, forbidden proof names, banned phrases/punctuation and prohibited formatting. Apply the meeting-duration exception only to the existing qualifying body invitation. Keep greeting/opener rules, evidence-copy checks, one-question checks and body word limits body-specific; retain the separate subject word cap. Require a nonblank subject.

Determine the selected row's permitted proof name once, using `external_ok is True`. References to that name remain allowed regardless of other rows sharing it. Other known disallowed proof names still block; preserve the existing prospect/evidence-subject exemption.

Adoption sentences require both a permitted category and the exact configured text, in addition to existing account/date/review checks. `none_found` and `unknown` never authorize a sentence. Ordinary outreach without an adoption sentence does not acquire new adoption requirements.

Extend the existing lightweight formatting checks to the reproduced Markdown forms, regional-indicator flags and keycap emoji. Preserve ordinary apostrophes, plain URLs and non-emoji international text. Document these as mechanical checks for supported forms; meaning and unusual formatting still receive human review. Do not add Markdown parsing or Unicode-data dependencies.

### 4.2 ARR ordering and wording

Keep the existing requirement that the adapter returns ranked rows. Validate the full key `(-net_change_usd, account_id)` before applying the cap. Reject incorrect order rather than silently choosing different accounts. Use ordinary case-sensitive string order for opaque account IDs and document it in the adapter contract.

Make the existing ARR literal rule case-insensitive and include the explicit phrase `annual recurring revenue`, allowing normal whitespace variations. Continue checking digits, currency/percentage markers and the reviewed fixed template. Do not invent a financial-language classifier. Keep the greeting separate so real account names containing digits are not rejected as monetary claims.

### 4.3 Refresh paths and deleted content

Normalize source roots and repository-relative watch/ignore paths once using POSIX path semantics. Remove harmless `.` segments; preserve rejection of absolute paths, traversal and symlinked evidence. Match watch directories by complete path components, including nested directories; `offers` must not match `offers-old`.

Report added, modified and deleted watched files. Keep Git's existing `--no-renames`: a rename appears as deletion plus addition, avoiding rename-detection machinery. A deleted entry identifies its prior revision/path so the reviewer can inspect its old content. Apply normalization to individually watched files as well.

Deleting an unbound watched page must be visible in the report; it need not permanently block a reviewed source update. Missing claim evidence or explicitly required watch files remain blockers. Proposed source stamps still remain proposals until the existing exact review/apply process completes.

Remove `verify_rows()` and `write_tracks()` after replacing their tests with tests of the actual committed-blob reporting/writing path in temporary Git repositories. Preserve case/whitespace and dirty-working-tree isolation coverage.

### 4.4 Verdict parsing and repository checks

`scan_verdict.py` accepts only known object envelopes: `qualified`, `no_usable_signal`, or `unusable`, with the fields required for that outcome. Require complete qualified bundles with a known tier, nonblank signal ID and canonical `YYYY-MM-DD` date. Taxonomy membership remains checked by evidence qualification, avoiding another configuration dependency here. The evidence gate already resolves valid event-date fallback; a qualified bundle without its governing date is unusable. Parse dates and sort by ordinal; preserve tier preference and report-order ties. Retain declared unusable/no-signal outcomes as coverage limitations. Reject malformed records with JSON and exit 2, never a traceback or fabricated checked evidence.

`check_repo.py` detects a checkout through `git rev-parse`, not the filesystem type of `.git`. Use Git enumeration for ordinary checkouts and linked worktrees. Keep the non-Git export fallback, without accidentally enumerating a parent repository. Test both checkout forms against the same intentionally tracked private file.

## 5. Minimal run preflight

### 5.1 Files and commands

Add `_templates/run/inputs.json` and one runtime module, `scripts/run_checks.py`. The module contains straightforward validation functions for the eight known workflows and calls existing helpers directly. Share each helper's complete validation entry point with its CLI; move necessary CLI-only checks into that path. In particular, evidence replay requires an actual aware, nonfuture fetch timestamp and must not use `grade()`'s default of now. `runs.py` owns CLI/lifecycle integration. No manifest entry can select a command, executable, argument string, Python module or dependency graph.

`inputs.json` starts as `{"schema_version": 1, "effects": {}, "gaps": []}`. Each workflow adds only its named input fields from the table below. Paths are run-relative regular files/directories, validated with the existing traversal/symlink protections. Source Git repositories use an explicit CLI `--source` path and a pinned revision in the manifest; they are not discovered by crawling.

Add `runs.py preflight RUN_ID [--source PATH] [--arr-packet -]`. It is read-only, returns structured outcomes/issues and derived handoff eligibility, and uses the same validation function as `record-review`. Extend `record-review` with those two optional inputs where applicable. Existing gates remain independently callable.

No new run-state enum or caller-authored purpose flag is needed. Existing Effect headings determine whether effects are proposed. Every proposed effect must have a corresponding `inputs.json.effects` entry naming a supported effect kind and its checked subject/input. No extra or omitted IDs are accepted. Validate all proposed effects before recording any subset as approved.

An example effect binding is `"A1": {"kind": "draft", "input": "packet.json"}`. Supported kinds are account_create, owner_transfer and contact_create for prospecting; draft for outreach/ARR; task for follow-up; and configuration for setup/refresh. Other workflows cannot propose effects. A dependent new-account contact names its account effect; only this existing dependency is supported, not arbitrary effect graphs.

| Workflow | Named inputs and preflight work |
|---|---|
| `signal-scan` | `sources`: receipt/page/result entries; optional `crm` packet. Re-grade retained evidence with actual fetch timestamps, validate the scan route and derive the verdict. Zero fetched pages or unavailable CRM may produce a limited finding, never an actionable handoff. |
| `signal-prospector` | `sources`; `candidates`: routing receipt/result plus source associations and permitted contact evidence. Re-grade sources, require matching account domains/signal IDs/tiers, rerun routing, and bind each proposed effect to an eligible candidate and allowed write kind. Adoption-assisted admission also requires its reviewed aggregate evidence. |
| `signal-outreach` | `handoff`, retained source receipt/page/result, `packet`, and saved gate result; optional refreshed receipt/page/result. Re-grade current evidence, match the packet's evidence-derived fields to it, check source provenance/route, and rerun outreach. Preserve original handoff artifacts; use the refresh rules below. Allow separate enrichment such as vertical. |
| `signal-followup` | `handoff`, `packet`, `mode`, saved gate result. Verify standard/ARR attribution against the frozen reviewed handoff and rerun the follow-up check with current sent/CRM prerequisites. Do not replay outreach's public-source freshness window after an actual send. |
| `signal-user-scan` | `bundle` plus permitted CRM/aggregate adapter receipts. Rerun privacy/category/date checks and check normalized owned-account/no-open-deal prerequisites. Unknown/failed coverage is a report with no actionable category. |
| `prospect-setup` | `postimages`, source revision, source/intake references and saved setup report. Validate proposed configuration, pinned evidence and bindings. Installation effects require the existing expected-after hashes. |
| `signal-refresh` | `postimages` when changing configuration, source revision and saved source report. Reproduce pinned source and binding checks; validate proposed configuration without imposing unrelated provider-readiness requirements. A no-change report needs no installation effect. |
| `signal-arr-growth` | Safe proposed drafts and permitted adapter/selection receipt; raw packet only through stdin. Run the ARR gate in memory and compare each selected draft/account with its proposed effect. |

The manifest stores paths and associations, not another copy of packets, policy or procedures. Expand the selected workflow's packet contract with this small field list; do not create eight new schema files.

For setup/refresh, bind each saved diagnostic source report to the exact retained factory inputs and prior revision that produced it, using the existing proposal/preimage artifacts. Replay diagnostics against that baseline. Separately validate final postimages at their proposed pinned revision; changed stamps and source revision are expected there. Do not compare a pre-stamp diagnostic report to a post-stamp factory and call the intended changes drift.

### 5.2 What preflight establishes

- Recompute deterministic outcomes from retained inputs. A saved `allow` or `passed: true` is insufficient. Compare substantive saved verdict/payload fields with recomputation; evaluation timestamps alone are not payload identity. Never refresh an original fetch timestamp by re-reading a saved page.
- Treat incomplete/failed checks as explicit findings when no effects are proposed. If an effect depends on them, block review recording for that proposal. Return structured input errors for malformed manifests; missing sources in a deliberate partial report require an explicit gap.
- Derive handoff eligibility for each selected artifact/subject from completed workflow prerequisites, not from an editable assertion. A valid report or human review alone does not establish it. A held candidate must not invalidate unrelated qualified candidates. Downstream workflows revalidate the required chain and cannot elevate a partial report into action eligibility.
- A handoff names source run/workflow, the actual review reference, selected artifacts and their hashes. Use only the exact named local run or explicitly supplied portable export. Compare copied artifact hashes and reproduced evidence; do not require unrelated prior-run contents or a surviving source checkout on another host. Local validation does not authenticate the human reference.
- Preserve outreach's existing re-fetch path: original handoff hashes verify provenance; a new local fetch has its own receipt, page and actual fetch time linked to the same selected account/source/signal. Do not require its page hash or timestamp to equal the original, and never mutate the reviewed scan. Changed substantive signal facts require review of the revised finding/bundle. Follow-up checks frozen send attribution and current task prerequisites, not whether the earlier drafting evidence would still qualify today.
- Source semantics, alias ownership, native provider-field mapping and the exact visible proposal remain human checks. Preflight binds gate-approved normalized payloads to effect IDs; it does not parse arbitrary review prose into a second action payload.
- Before actual effects, repeat current preflight and the existing live preimage/suppression reads. Changes to selected subjects or proposed payloads require revised review; never substitute another candidate after approval.

`record-review` stores a compact validation object inside existing `review.json`: contract version, validation time, derived outcomes/eligibility and hashes of the checked inputs. Include the manifest and all retained referenced inputs/results in the existing snapshot automatically. Keep `01_review.md`'s artifacts list for additional review material; users need not enumerate the same machine inputs twice.

`status` verifies the frozen validation record and snapshot without rerunning today's freshness rules against completed historical work. Relevant edits invalidate approval as before. Do not create a second validation ledger or automatically rewrite reviewed files. The preflight report must expose its failed checks before the user reviews a partial finding.

### 5.3 ARR privacy exception

Both preflight and record-review accept `--arr-packet -` only for ARR. Consume it in memory; never echo, spool or save its raw packet or financial gate output. Persist only the retention-authorized projection: data date, adapter receipt reference, selected account/effect IDs, exact drafts, counts and necessary permitted hold reasons. Do not retain raw-series hashes by default either.

The stored validation explicitly says financial inputs were transient and cannot be replayed from saved artifacts. Before draft creation require a fresh streamed packet; selected approved accounts and draft fields must still match. Compare relevant selection prerequisites with still-available in-memory originals or an authorized immutable adapter receipt that identifies the original inputs; a query execution ID alone is insufficient. If neither comparison is possible after session loss, prepare a fresh review and obtain approval rather than claiming the old preimage is unchanged. A changed financial preimage follows the existing revised-review rule even if the draft matches. If the required minimal receipt cannot be retained, preserve the existing unavailable-workflow outcome.

### 5.4 Route-scoped snapshots and compatibility

Add explicit factory input paths to each route in `wrapper-contract.json`; retain `checks` for helper dependencies. Update registry validation/generation together and increment its schema version. Choose paths from this fixed table, without selector expressions:

| Workflow | Factory files in review snapshot |
|---|---|
| Setup, refresh, outreach | Policy, adapters, ICP, taxonomy, claims |
| Scan | Policy, adapters, taxonomy |
| Prospector | Policy, adapters, ICP, taxonomy |
| Follow-up | Policy, adapters; taxonomy/claims additionally in standard mode |
| Adoption scan | Policy, adapters |
| ARR | Policy, adapters, ICP |

Match actual helper dependencies to this table. In particular, the ARR route/territory path must not load unused taxonomy through the prospect-admission loader. Use a small account-rule loader reused by the full routing loader.

Keep whole-policy and shared lifecycle/helper hashes conservative. Remove the global policy `review_inputs` setting from new configuration; it is redundant with route ownership. Recognize an old setting only to explain that it is obsolete, never to omit new mandatory dependencies.

Old run records remain readable. They cannot support another effect or actionable handoff until their required inputs have been prepared, validated and reviewed under the new contract. Do not invent missing artifacts or retroactively stamp old approval. No bulk run migration is required.

## 6. Remove ambiguity and reduce reading load

Admission remains a fixed invariant: one Tier 1 or two distinct Tier 2 signals, with the existing adoption exception. Keep the executable owner in `route_candidate.py`. Remove the unused `prospector.admission` string and descriptive routing entries from new policy examples; retain real settings such as house owner IDs. Workflows reference the owning rule instead of restating configurable-looking thresholds. For deployed legacy settings, accept only the old equivalent defaults as deprecated; report conflicting values explicitly rather than silently ignoring them. No automatic configuration rewrite.

Divide setup's Load guidance into interview, evidence intake, and proposal/installation phases within the existing workflow. This is progressive reading, not new folders or run stages. Read installation/bootstrap instructions only when files are missing; load only selected optional adapter sections; keep source manifest/CLI shape in the helper docstring/`--help`, and put configuration meaning in its owning examples. Ordinary setup should not require reading Python implementations.

Measure representative phase loads with the synthetic factory, including always-loaded routing/rules and selected references. Aim for the ICM 2k–8k range before user materials; record the measurement method and paths. Do not hide mandatory context or call a chars/4 estimate an exact token count. Large supplied materials remain bounded by the existing source/extraction process.

Keep generated pointers and useful human-review reminders. Avoid copying policy tables into this spec's replacement documentation. After implementation, durable behavior belongs in workflows/helper contracts; this maintenance spec is not a new authority layer.

## 7. Implementation order and completion checks

1. **Inputs/configuration:** shared primitives, local gate shape checks, configuration checks and warm-engagement handling (A02–A04, A19).
2. **Existing behavior:** messaging/lint, ARR, source filtering, verdict parsing and worktree detection (A05–A14).
3. **Run contract:** preflight, manifest, evidence associations, transient ARR support, snapshots and old-run behavior (A01, A18).
4. **Cleanup/docs:** policy ownership, production-path tests, phased setup loading and regenerated wrappers (A15–A17).

Keep these as reviewable change groups; no partial release should claim the whole audit is resolved. Each group includes its corresponding tests and contract updates. Stop expanding once the specified behavior and regressions pass.

Use existing test modules and fixtures. Add one focused run-preflight test module only if it makes the expanded lifecycle cases easier to read. Favor table-driven malformed-input cases over repetitive test scaffolding. Keep synthetic providers; no live CRM/mail/warehouse calls are required for implementation validation.

Beyond the traceability table, require these integrated cases:

- A normal scan → outreach → proven-send follow-up still works with exact review and no automatic provider effects.
- A fabricated saved passing result disagrees with replay and blocks its effect; changing the packet/source after review makes the record stale.
- Missing, naive or future fetch timestamps fail through both standalone evidence validation and preflight/record-review; no entry point silently replaces them with now.
- An evidence bundle copied from another account, mismatched source artifact, stale source review or wrong handoff attribution blocks the affected handoff/effect.
- A legitimate outreach re-fetch preserves original handoff provenance and uses new fetch metadata; follow-up after a proven send does not fail merely because the old public-source check exceeds the drafting freshness window.
- Public-only, no-signal, unknown-adoption, disabled-module and blocked-effect reports remain usable as limited findings, with no actionable handoff.
- Ordinary outreach works without optional adoption input. A mixed prospect report can retain held candidates while proposing effects only for eligible ones.
- Setup/refresh expected-after, partial-apply recovery and unapproved-postimage protections still work. Initial diagnostics and final stamped-postimage validation compare against their respective factory baselines.
- Passage of time does not erase historical completion; a new effect attempt still performs current freshness and live-preimage checks.
- A claims-only edit does not stale a scan; relevant taxonomy edits do. Standard follow-up still tracks claims/taxonomy; ARR follow-up does not require them.
- ARR transient input and raw financial output appear in neither saved files nor preflight stdout/error output. Only approved accounts/drafts survive revalidation; changed preimages are surfaced.
- Existing valid fields and boundary cases still pass: real title extensions, allowed selected proof, supported address syntax, empty completed reads, timezone boundaries, exact cap/tie behavior and no-change refresh.

Final implementation checks:

```bash
python3 -B scripts/wrappers.py --check
python3 -B scripts/check_repo.py
python3 -B -m unittest discover -s tests -v
git diff --check
```

Done means every A01–A19 row has its regression/acceptance evidence, all checks pass, the ICM walk is repeated, and changed behavior is documented at its owner. The completion report names any remaining live-adapter uncertainty. No new dependency, external service, automatic publishing, automatic configuration migration or external write is part of this spec.

## 8. Implementation and verification record

All A01–A19 findings are implemented. The existing eight workflows, folder layout,
standard-library runtime and run states remain. The only new runtime module is
run_checks.py; inputs.json is the single new run manifest. Configuration, fixed
checks and human judgment remain in their respective factory, helper and review
owners. Removed policy strings, duplicate refresh functions and repeated lint
validation have not been replaced by a framework.

| Findings | Verification owners |
|---|---|
| A01, A18 | [Preflight regressions](tests/test_run_checks.py), [lifecycle](tests/test_workflow.py), [integrated workflows](tests/test_end_to_end.py), [setup](tests/test_setup.py) |
| A02–A04 | [Routing](tests/test_route_candidate.py), [follow-up](tests/test_followup_gate.py), [ARR](tests/test_arr_growth_gate.py), [outreach](tests/test_outreach_gate.py), [configuration](tests/test_setup.py) |
| A05, A16 | [Committed-source refresh](tests/test_refresh_tracks.py), [source safety](tests/test_safety_boundaries.py) |
| A06–A09, A14 | [Outreach and surface checks](tests/test_outreach_gate.py) |
| A10 | [Verdict envelopes and dates](tests/test_scan_verdict.py) |
| A11 | [Checkout and worktree enumeration](tests/test_check_repo.py) |
| A12–A13 | [ARR ordering and template restrictions](tests/test_arr_growth_gate.py) |
| A15 | [Legacy policy validation](tests/test_setup.py), [routing](tests/test_route_candidate.py) |
| A17 | Phase measurements and ICM walk below |
| A19 | [Warm-engagement coverage and routing](tests/test_route_candidate.py), [handoff prerequisites](tests/test_run_checks.py) |

Two independent verifiers reviewed the finished gates/configuration and lifecycle.
Their additional counterexamples exposed six issues: Git-quoted Unicode paths,
international names collapsing during alias comparison, wrong-account follow-up
targets, malformed manifests hidden by gap explanations, internal adoption domains,
and mismatched aggregate receipt references. All six were repaired, regression
tested and independently rechecked. Both verifiers reported no remaining actionable
findings in their assigned scopes.

Final checks: **306 tests passed** (baseline 241); generated wrappers match;
repository checks pass for **8 routes and 95 public files**; `git diff --check`
passes. Tests use synthetic data and temporary workspaces, including real local
Git history and linked worktrees. They do not establish live adapter truth,
semantic source fit or actual human consent. No live provider writes or publication
were performed.

The ICM walk was repeated from AGENTS.md through the root router, selected family,
workflow phase, private run inputs, review and result. Required inputs now derive
effect readiness; a reviewed partial finding does not acquire action eligibility.
Factory changes are scoped to the consuming routes. The independent lifecycle
verifier also confirmed the walk and the phase measurements.

Representative fresh-setup loads, **estimated as characters divided by four**:

| Phase | Characters | Estimated tokens |
|---|---:|---:|
| Interview | 28,783 | 7,196 |
| Source intake | 26,179 | 6,545 |
| Proposal: settings | 30,026 | 7,506 |
| Proposal: messaging | 29,895 | 7,474 |

Every estimate includes AGENTS.md, CONTEXT.md, workflows/knowledge/CONTEXT.md,
_shared/rules.md, the setup workflow and workflows/run.md except its explicitly
skipped Named handoffs section. Interview adds the questionnaire, example ICP,
identity/voice/module-enable settings and installation bootstrap/module guidance.
Intake adds the source/retention adapter sections and source_snapshot --help.
Settings adds those adapter sections, example policy/ICP and validate_setup --help.
Messaging adds those adapter sections, example ICP/taxonomy/claims and the
refresh_tracks, build_pairings and validate_setup help outputs. These estimates
exclude user materials, are not tokenizer measurements, and do not require reading
Python implementations during setup.
