# Installation

## Local agent

Keep the repository intact. Python 3.9+ is needed only for local checks and run helpers.
Copy the factory examples once, preserving an existing configuration:

```bash
cp -n _shared/policy.example.json _shared/policy.json
cp -n _shared/adapters.example.md _shared/adapters.md
cp -n _shared/icp.example.md _shared/icp.md
cp -n _shared/taxonomy.example.json _shared/taxonomy.json
cp -n _shared/claims.example.json _shared/claims.json
python3 -B scripts/check_repo.py
python3 -B -m unittest discover -s tests -v
```

For an existing deployment, review differences against the examples; never
overwrite configured values with starter defaults. Configuration and run data
remain ignored by Git.

Fill the [questionnaire](questionnaire.md). Keep mode example for synthetic
use; set mode live only after required adapters and workflow settings are
configured and reviewed. No command here installs a connector or creates
a schedule. Missing private adapters remain explicit unavailable capabilities.

Codex-compatible skill pointers are tracked in .agents/skills/; Claude slash
command pointers are tracked in .claude/commands/. Work from this repo root.
If a host does not discover those directories, explicitly read AGENTS.md
and invoke the canonical workflow. The workflow remains the authority.

## Configure the workspace

Use the examples as the field reference and keep each fact in its owning file:

- `policy.json`: identity, timing, workflow limits, email voice and enabled capabilities.
- `adapters.md`: tools, exact provider field maps, complete-read criteria, write scope, readback and private retention.
- `icp.md`: territory, ranked verticals, disqualifiers and personas. Its frontmatter is a JSON object between `---` lines, followed by prose.
- `taxonomy.json`: a flat signals list with integer tiers, source, freshness, creates_work, recipient titles and claim bindings.
- `claims.json`: bounded claims, verbatim evidence, proof permissions and approval stamps. Keep source revision and content-unit stamps distinct.

Example claims and signals are unapproved. Configure a versioned knowledge
source and use [signal-refresh](../workflows/knowledge/signal-refresh.md) to
prepare and review exact factory changes. Changed or translated content needs
fresh review; recomputing a hash does not grant approval. Bind every claim to
a signal and generate the local view with `python3 scripts/build_pairings.py`.

Outreach also needs a supplied or configured approved voice anchor. Its reviewed
packet includes claim.pick_reason explaining the quote-to-claim connection.
Fit warnings do not waive claim approval, evidence or recipient checks; the
configured blocking mode can hold a fit gap for review.

The optional adoption and billing workflows ship adapter contracts, not SQL or
warehouse access. Implement adoption_lookup, adoption_territory and billing_growth
against your own schemas and permissions. Both private capabilities default
disabled. Keep private data, credentials and voice samples outside the public
template; configure permitted retention before saving customer review artifacts.

Validate the configured adapters with synthetic cases and an authorized read-only
live check before enabling their live capabilities. Local checks do not establish
provider permissions, complete warehouse data, email meaning or human approval.
Changes to selected contracts, helpers or inputs invalidate existing run reviews;
prepare a fresh review for the next effect and preserve earlier results.

## Perplexity Computer

Install the canonical AGENTS.md, CONTEXT.md, workflows/, _shared/, _templates/
and scripts/ into one new Project, preserving relative paths. Configure the
local deployment files there. Before a run, sync Project Files into the
current sandbox through the host's project-file sync capability.

Create each saved Project skill from the matching .agents/skills/NAME/SKILL.md
pointer. Keep its procedure in Project Files; do not copy the full workflow
into the skill. A standalone pointer without its repository files is incomplete.
Verify the host resolves those paths with a synthetic read-only run.

Perplexity output/{run-id}/ lives in the session sandbox and is shared for
review in the thread. Do not sync it back into reusable Project Files.
Persist or export a run privately only if resumption is required. Across
sessions, pass the exact reviewed artifact explicitly; never assume sandbox
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
