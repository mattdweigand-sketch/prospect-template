# Local tooling

Inputs: scripts/wrapper-contract.json, the selected workflow, explicitly named
run inputs and its configured factory. No helper makes a network request.
Python 3.9+ standard library only; factory configuration uses canonical JSON.

| Tool | Job |
|---|---|
| wrappers.py | Generate/check root/family routers and thin skill/command pointers |
| runs.py | Copy a run starter, record an actual review reference, inspect review/result state |
| run_checks.py | Validate one run's fixed input manifest with its complete workflow gates |
| evidence_gate.py | Match full-page quote, attribution and dated evidence; preserve actual fetch timestamp |
| scan_verdict.py | Pick newest qualified Tier 1, else Tier 2, preserving report-order ties |
| route_candidate.py | Distinct-type admission, territory/disqualifiers, ownership/open-deal routing |
| privacy_check.py | Exact aggregate bundle fields/types, person-data leakage and category consistency |
| outreach_gate.py | Claim/signal/persona approval, recipient, freshness, suppression and draft constraints |
| lint_draft.py | Configured cold-email phrase, word-limit, punctuation and formatting checks |
| followup_gate.py | Unique sent proof, contact, duplicate task and timezone-aware due date |
| arr_growth_gate.py | Complete growth candidate packet, routing/suppression, fixed template and cap |
| refresh_tracks.py | Pinned-commit evidence report and separate proposed factory postimages |
| source_snapshot.py | Version explicitly supplied materials privately; preserve provenance and prior history |
| validate_setup.py | Check deployed/proposed ICP, bindings, approvals, voice and pinned source evidence |
| build_pairings.py | Rebuild ignored pairings.md; reject unknown/unreachable claim bindings |
| approval.py | Detect changed approved content units; never grant authorization |
| factory.py | Read canonical factory files; validate selected policy sections and comparison identities |
| check_repo.py | Links, routes, public-template hygiene and example contract checks |

Outputs: JSON on stdout for gates; explicitly requested generated wrappers,
run artifacts or staged factory postimages for the writing helpers. Packet
shapes and CLI options live in each helper's docstring/--help; procedure and
meaning live in the selected workflow. Gate exits: 0 pass, 1 held/blocked,
2 unusable input, except routing returns 0 for any valid route (check claimable)
and scan_verdict returns 0 for a valid no-signal finding (check recommended).
Repository checks return nonzero on failure. A check is not approval.
Evidence and follow-up replay use --now with a full timezone-aware timestamp;
normal runs use the current time and configured identity.timezone.

Human check: inspect the diff, cited sources, exact effect and provider evidence.
The run snapshot hashes selected helper dependencies from wrapper-contract.json
as well as contracts/configuration. Editing a selected gate invalidates review.
No helper chooses a customer run, sends mail, approves its own proposal or proves
provider completion. Use explicit --shared temporary fixtures for synthetic work;
there is no implicit fallback to examples in production helpers.

Run `python3 -B scripts/check_repo.py` and
`python3 -B -m unittest discover -s tests -v`.
