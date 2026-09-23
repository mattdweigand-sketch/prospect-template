---
type: workflow
command: signal-refresh
mode: write
---
# signal-refresh

Propose claim-library updates from a configured, versioned knowledge source.

## Load / Skip
- Working: output/{run-id}/request.md and only its explicitly named inputs. On resumption, read that run's 01_review.md, review.json and 02_result.json.
- Reference: _shared/policy.json (identity and the sections named below), _shared/rules.md, _shared/adapters.md; load _shared/icp.md, _shared/taxonomy.json and _shared/claims.json only where a step names them.
- Lifecycle: [workflows/run.md](../run.md). Required adapter capabilities: knowledge source.
- Skip: other runs, other workflow families, private example data, and unrelated factory sections. A missing adapter is a named limitation or blocks its dependent effect.

## Process
1. Open the configured knowledge source at a pinned revision. Read the current claims' source references and the source paths named in policy.refresh. No other prospect workflow reads the whole knowledge source.
2. Verify existing evidence against its source, identify changed pages since the recorded revision, and inspect the specified ICP and contradiction paths. Keep source types distinct: customer report, product statement, inference and evaluation advice.
3. Propose changes to _shared/claims.json, _shared/taxonomy.json or _shared/icp.md as exact numbered diffs. Each claim carries id, kind, claim, limit, source reference, evidence, signal bindings, verticals, personas, optional permitted external proof and review status.
4. Preserve held and disputed claims until their revisions are explicitly reviewed. Propose the corresponding taxonomy bindings and persona changes together so consumers cannot select a partially migrated row. A source revision update alone never approves new wording.
5. On exact approval apply only the listed configuration changes, validate JSON and referenced IDs, and rebuild any generated views. Record the reviewed source revision and actual approval reference. Do not write to the upstream knowledge source.
6. Read back all changed files. If either the configuration or source preimage changed since review, stop and show a revised diff. A review marker records an assertion; it is not proof of approval or evidence truth.

## Outputs and readiness
- output/{run-id}/01_review.md contains the requested review and exact numbered effects, source coverage, evidence and unresolved items.
- Ready when the scope is reconciled, findings have source references, required checks above pass, and gaps cannot be mistaken for checked evidence. Unsupported effects are withheld explicitly.
- output/{run-id}/review.json records the user's review of this exact revision.
- output/{run-id}/02_result.json follows the shared run contract. Every approved effect has an outcome and any provider/readback references.

## Human check
Read every proposed claim and limit against its actual source. Approve exact row and binding changes; keep unsupported or disputed claims held.
