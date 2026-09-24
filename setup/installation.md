# Installation

## Runtime contract

Keep the repository intact and preserve relative paths. The harness needs:

| Capability | Purpose |
|---|---|
| Read/write workspace files | Load canonical workflows, stage configuration, keep exact review artifacts |
| Execute Python 3.9+ and Git | Run standard-library gates and verify versioned messaging evidence |
| Present a review and receive explicit human approval | Apply only the exact approved configuration or external effect |
| Retain or privately export deployment inputs | Resume with the same evidence, source revision and review state |
| Required provider tools for the selected workflow | Search/fetch, CRM, mail or optional private adapters, with complete reads and readback |

No particular model, model-provider SDK, browser or agent host is required.
An agent without local execution can use an authorized execution environment
with these capabilities; it must not substitute its own judgment for a gate it
cannot run. Provider credentials stay in the host's credential mechanism.
See [optional host entrypoints](hosts.md) for wrapper conventions.

## Guided configuration

Start by asking the agent to
**run setup**, or invoke `prospect-setup`. The [guided workflow](../workflows/knowledge/prospect-setup.md)
conducts the interview and prepares exact configuration changes for review.
Run this Python snippet to copy missing factory examples without replacing
an existing configuration:

```python
from pathlib import Path

for source in Path("_shared").glob("*.example.*"):
    destination = source.with_name(source.name.replace(".example", ""))
    if not destination.exists() and not destination.is_symlink():
        with destination.open("xb") as output:
            output.write(source.read_bytes())
```

Then run the repository checks:

```bash
python3 -B scripts/check_repo.py
python3 -B -m unittest discover -s tests -v
```

For an existing deployment, review differences against the examples; never
overwrite configured values with starter defaults. Configuration and run data
remain ignored by Git.

Run preparation now uses workflow-specific input paths from the wrapper registry.
The old policy.review_inputs list is no longer used; remove it in the next
reviewed configuration update. Also remove prospector.admission and routing's
descriptive route strings. Their historical defaults remain accepted during
migration, but conflicting strings are rejected because routing and admission
are fixed code checks. routing.house_owner_ids remains configurable. Existing
run receipts remain historical records; prepare and review the required inputs
under the current contract before another effect or handoff.

The agent uses the [questionnaire](questionnaire.md) to fill missing answers.
Keep mode example while preparing messaging and synthetic previews; set mode
live only after required adapters and workflow settings are
configured and reviewed. No command here installs a connector or creates
a schedule. Missing private adapters remain explicit unavailable capabilities.

Work from the repository root. If a host does not discover optional wrappers,
explicitly read AGENTS.md and invoke the named canonical workflow.

## Configure the workspace

Use the examples as the field reference and keep each fact in its owning file:

- `policy.json`: identity, timing, workflow limits, email voice and enabled capabilities.
- `adapters.md`: tools, exact provider field maps, complete-read criteria, write scope, readback and private retention.
- `icp.md`: territory, ranked verticals, disqualifiers and personas. Its frontmatter is a JSON object between `---` lines, followed by prose.
- `taxonomy.json`: a flat signals list with integer tiers, source, freshness, creates_work, recipient titles and claim bindings.
- `claims.json`: bounded claims, verbatim evidence, proof permissions and approval stamps. Keep source revision and content-unit stamps distinct.

Before live outreach, configure outreach.task_status_map with every provider
task status that can appear in the complete activity read. Values are completed,
open or cancelled. The empty example map is deliberately unconfigured. Unknown
statuses stop the gate; configure native suppressing_task_subtypes separately.
Follow-up task values and closed_statuses are also provider mappings, not fixed
CRM defaults. Verify them against provider receipts before live use.

Example claims and signals are unapproved. [prospect-setup](../workflows/knowledge/prospect-setup.md)
accepts an existing versioned knowledge source or creates a private Git snapshot
of supplied documents and attributed interview statements. It prepares the ICP,
claims, signal bindings and sample emails; users do not have to author the JSON.
Use [signal-refresh](../workflows/knowledge/signal-refresh.md) for later changes
in that source, or rerun setup to revise targeting, voice or supplied materials.
Changed or translated content needs fresh review; recomputing a hash does not
grant approval. Bind every claim to
a signal and generate the local view with `python3 scripts/build_pairings.py`.

Outreach also needs a supplied or configured approved voice anchor. Its reviewed
packet includes claim.pick_reason explaining the quote-to-claim connection.
Fit warnings do not waive claim approval, evidence or recipient checks; the
configured blocking mode can hold a fit gap for review.

Validate proposed or installed messaging with:

```bash
python3 scripts/validate_setup.py --source SOURCE_CLONE
```

For staged proposals also pass --shared output/RUN_ID/postimages. The source is
the explicit local clone or retained setup snapshot. Checks use the claim
library's pinned commit. A passing messaging report does not verify connectors,
semantic fit or actual approval. Keep source snapshots privately available for
future refresh; they are deployment inputs, never public template content.

## Choose business modules

| Module | When it fits | Enablement |
|---|---|---|
| Core B2B research and outreach | Products or services sold to identifiable business accounts and contacts | Configure ICP, supported claims, public signals and required CRM/mail adapters |
| Subscription adoption | A business with individual paid users and organization subscriptions | policy.adoption.enabled; reviewed adoption_lookup and optional adoption_territory adapters |
| Self-service ARR growth | A subscription business with complete daily recurring-revenue data, normalized to USD, and permitted billing contacts | policy.arr_growth.enabled; reviewed billing_growth adapter and fixed email template |

Optional modules default disabled and are not prerequisites for the core. Setup
must confirm business-model fit before enabling them; do not invent subscription
or revenue data for a service business. Their contracts are not preinstalled SQL
or warehouse access. Keep private data and voice samples outside the public
template; configure retention before saving customer review artifacts.

Validate the configured adapters with synthetic cases and an authorized read-only
live check before enabling their live capabilities. Local checks do not establish
provider permissions, complete warehouse data, email meaning or human approval.
Changes to selected contracts, helpers or inputs invalidate existing run reviews;
prepare a fresh review for the next effect and preserve earlier results.

## Ephemeral execution environments

If the host copies workspace files into a temporary environment, verify the
same relative paths and configured bytes before each run. A standalone command
pointer without its referenced files is incomplete. Share output/{run-id}/
privately for review; never publish it into the reusable template.
Persist or export a run privately if resumption is required. A setup-created
knowledge snapshot must be retained privately while referenced by the deployment,
or replaced with an approved durable source. Across sessions, pass the exact
reviewed artifact explicitly; never assume temporary workspace
files survive. The configured CRM and mail provider retain external business state.

## Start a run

The task supplies a fresh ID. For example, after choosing `demo-001`:

```bash
python3 scripts/runs.py init demo-001 signal-scan
python3 scripts/runs.py status demo-001
```

Follow the workflow selected by [the root router](../CONTEXT.md), then the
[run contract](../workflows/run.md). No external action follows merely from
creating the starter. An example claim cannot be used in live outreach.
