# Review source changes

## Inputs

| Source | File/Location | Section/Scope | Why |
|---|---|---|---|
| Procedure | `procedure.md` | Full file | Detailed steps, report and stop conditions |
| Procedure | `../procedure.md` | Full file | Canonical setup validation, exact approval and application lifecycle |
| Reference | `../references/installation.md`; `../references/source-format.md` | Full files | Source mode, retention and evidence requirements |
| Working | Active .local/config/sources.json and approval.json | Applied baseline and source revision | Compare against actual installed state |
| Working | Proposed full source commit or new permitted snapshot | Changed, missing and related watched sources | Assess changes and watch coverage |

## Process

Step numbers match `procedure.md`; it owns the detailed rules.

1. Load the applied configuration and inspect the proposed full source commit.
2. Compare watched files and inspect related files for missing coverage.
3. Stage a setup update recording both revisions and affected claims.
4. Revise only affected content and coverage; review contradictions, retirements and claim meaning.
5. Refresh previews, validate and prepare; run the Audit and present the complete review.
6. After exact review approval, apply through setup and rerun the requested preflight.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|---|---|---|
| 5 | Source changes, affected claims, actual meaning review, complete prepared postimages and SHA | Review watch coverage and approve exact postimages, including date-only updates |

## Audit

| Check | Pass Condition |
|---|---|
| Comparison | Full old/new revisions, deleted sources, contradictions and coverage gaps are explicit. |
| Meaning | Changed claims retain source limits; unsupported wording is removed and dates reflect actual review. |
| Scope | Unrelated settings are preserved; setup’s previews, validation and prepare pass. |
| Application | Exact approval precedes setup application; changed inputs require a new review. |

## Outputs

| Artifact | Location | Format |
|---|---|---|
| Source comparison and proposal | Current chat and ignored `.local/setup/<run-id>/` | Revisions, changed sources, affected claims and complete prepared review |
| Applied update | Ignored `.local/config/` | Approved configuration and setup receipt, only after approval |

## Next

`../` owns prepare/apply; requested operational workflows resume after preflight.
