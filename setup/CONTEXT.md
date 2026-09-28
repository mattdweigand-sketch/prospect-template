# Configure the prospecting workspace

## Inputs

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Procedure | `procedure.md` | Full file | Detailed steps, report and stop conditions |
| Reference | `questionnaire.md`; `references/CONTEXT.md`; `references/installation.md`; `references/source-format.md` | Full files | Interview gaps, setup lifecycle and source requirements |
| Reference | `templates/CONTEXT.md` | Full file, then named templates as needed | Fictional scaffolding, never live configuration |
| Reference | `../shared/providers.md` | Full file | Verified provider mappings and capability gaps |
| Reference | `../shared/subscription-interface.md` | Only before enabling a warehouse branch | Optional-module data and private SQL contracts |
| Working | Supplied offer, ICP and voice sources; existing .local configuration when present | Permitted materials, full source revision and current state | Business facts, evidence, retention preferences and update baseline |

## Process

Step numbers match `procedure.md`; it owns the detailed rules.

1. Inspect sources and current configuration; ask only for gaps or conflicts.
2. Present the source mode and retention plan; stop before capturing material.
3. Capture only permitted sources or pin the existing repo; initialize a staged setup and configure business settings.
4. Record supported claims, quotes, limits, naming permission, voice and watched source paths.
5. Discover tools and map verified capabilities; leave unavailable capabilities unset.
6. Build three synthetic previews and record actual meaning, voice and retention review.
7. Validate and prepare; run the Audit, then present the complete review, SHA and limitations.
8. After exact review approval, apply unchanged postimages and verify the receipt.
9. Run preflight for the requested operational workflow.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 2 | Source mode and local retention plan | Confirm what may be retained before capture |
| 6 | Clear-fit, indirect-fit and rejected previews with claim and voice evidence | Review meaning, omissions, limits and retention |
| 7 | Complete prepared review, SHA, optional-module previews and provider gaps | Approve exact postimages before application |

## Audit

| Check | Pass Condition |
|---|---|
| Grounding | Claims, voice and optional-module wording have reviewed sources, limits and permissions. |
| Completeness | No fictional business values fill unresolved gaps; unavailable capabilities remain explicit. |
| Review | Three previews and enabled-module previews are inspected; validation and prepare pass. |
| Application | Proposal and active state still match the approved review; the applied receipt is read back. |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Setup proposal and review | Ignored `.local/setup/<run-id>/` | Staged configuration, previews, complete Markdown review and SHA |
| Applied configuration | Ignored `.local/config/` | Approved settings, source references and application receipt |
| Permitted sources and queries | Ignored `.local/sources/` and `.local/queries/` | Retained source snapshots and reviewed private SQL, only when needed |

## Next

Any requested operational workflow after its preflight and live tool discovery. Source changes use `refresh/`. Configuration approval does not authorize customer writes.
