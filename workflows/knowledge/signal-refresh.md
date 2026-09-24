# Refresh approved claims

Refresh the source established by prospect-setup: an upstream repository or a
retained private material snapshot. Prepare exact local factory changes; the
source repository remains read-only. New supplied materials go through setup.
An optional contradiction source uses the versioned JSON register defined in
_shared/adapters.example.md. Unsupported formats stop verification; an
unconfigured register is not evidence that no contradictions exist.

## Load / Skip

- Working: output/{run-id}/request.md and a fresh local clone of policy.refresh.source made through the configured read-only source adapter.
- Reference: workflows/run.md, _shared/rules.md; policy.json refresh and relevant email voice settings; claims.json, taxonomy.json and icp.md; adapters.md versioned knowledge source contract.
- Skip: CRM, mail, warehouse data, unrelated local wikis and memory as evidence. No configured source means an explicit gap.

## Process

1. Fetch the configured source with the configured clone_depth into an isolated temporary directory. Resolve the current source revision to a full Git commit. If the previous claims.source_revision is outside shallow history, fetch that exact history read-only or report an unresolved comparison; never silently reset the baseline. The script itself performs no network operations.
2. Run `python3 scripts/refresh_tracks.py --source SOURCE_CLONE --revision COMMIT`. It reads **committed blobs at that revision**, not the clone's working-tree files. The report names head/date, prior source revision, broken evidence, missing pages, changed content/watch pages, contradiction flags and unstamped units. End with one line only when unchanged and all unstamped/broken/missing/missing-watch/contradiction lists are empty.
3. Address unstamped units first: a row, signal or persona_cares changed since its approved hash. Propose approve-as-is, a precise revision or revert; a stale stamp never grants permission. For changed ICP watch pages, read the configured persona/ICP section and propose only justified persona/row edits. For open contradictions, read both claims and propose a limit, hold or reasoned no-change. An absent configured watch page is a gap to resolve, not evidence of no contradictions.
4. For each broken row/missing page, inspect the pinned revision and propose replacement verbatim evidence, a corrected source_reference or removal. A row without a defensible evidence sentence at that commit is removed/held, never reconstructed from memory. Deleted and renamed watch paths must be examined; they can invalidate previous assumptions.
5. Read changed pages in the configured source watch paths, including relevant product/service documentation and customer evidence. Skip redundant claims and pages without an evidence-backed connection to the configured buyer's work. Each candidate needs one verbatim sentence supporting something useful after a signal. Cap additions at refresh.max_new_rows; record skipped pages and reasons.
6. Each row proposal includes id, status, kind (reported_example, product_capability, inference or evaluation_advice), claim, limit, track, evidence, source_reference, verticals, personas, proof{name, external_ok}, approval_reference and approved stamp postimage. Claim strength must match the evidence; limit bounds what an email may not imply. Track is one concise sentence in the configured approved voice, within claim/limit, without copying eight evidence words. No invented product claims, numbers or proof names. A proof is externally nameable only with explicit evidence and review that it is a public customer story.
7. Use existing ICP persona/vertical IDs and bind **every new row** to at least one taxonomy claim_ids list. There are no new vertical-only rows. Propose creates_work, target_titles, claim_ids or persona_cares changes as separate numbered items. Use natural wording within each claim and limit.
8. Stage complete proposed factory files in output/{run-id}/proposal/. Do not alter active _shared files. Validate evidence against the pinned source using `--shared output/RUN_ID/proposal`. Prepare proposed stamps only in a fresh separate destination using `--stage output/RUN_ID/postimages --approve-rows EXACT_IDS --approve-signals EXACT_IDS --approve-persona-cares --stamp`, using only the applicable flags. These flags prepare proposed bytes; they do not grant approval. Unknown/wildcard unit IDs and active-factory staging are rejected. Leave every unselected unit's stamp untouched.
9. Run `python3 scripts/build_pairings.py --shared output/RUN_ID/postimages` and the synthetic tests. The generated pairings view is disposable and not an independent source of truth. Fix broken bindings before review. No source_revision advance may pass with broken/missing claim evidence. If source evidence or a proposed row changes, regenerate the affected postimages and review hashes.
10. Put complete diffs/postimages, pinned source report and exact effects in 01_review.md. Include SHA-256 expected_after entries for every active factory file the effect will change as specified by workflows/run.md. Linked row/binding changes should be one coherent effect, or explicitly dependent effects. Show added/fixed/cut rows, holds, proposed stamps and source revision. Do not include unapproved extra edits in a combined file postimage.
11. After actual exact approval, recheck active preimages and apply only approved postimages. Partial selections require recomputing the resulting files; if their bytes differ from the reviewed hashes, show and obtain review of the revised payload. Verify all landed hashes, re-run source/binding checks and rebuild local pairings. Report the source commit, row count, units stamped and each applied/held effect. A failed readback is recovery, not permission to overwrite.

## Outputs and readiness

01_review.md orders unstamped/contradiction issues, broken rows, candidate rows, taxonomy/persona edits and skipped pages. Include full row content, source path at the pinned commit, binding IDs and allowed proof naming. Declare source report, exact diffs/postimages and generated check reports as artifacts; expected_after covers the active configured inputs.

02_result.json cites each approved local effect and byte readback. Stamps detect edits; neither a stamp, source check nor test pass proves semantic truth or human approval.

## Human check

Review claim strength, limits, verbatim evidence, persona relevance, public naming permission and exact file changes. No upstream writes, publication, unrelated deployment edits or unselected approval stamps. Outreach reads the approved local claim library, never the knowledge repository directly.
