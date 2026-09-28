# Shared configuration and checks

The installed configuration lives in `.local/config/`, relative to the repository root. Tests explicitly opt into fictional `examples/config/`; production never falls back to it.

| Installed file | Owns |
|---|---|
| policy.yaml | Identity, workflow limits, status mappings, optional modules, retention and approval boundaries |
| icp.md | Target companies, buying entities and evidenced responsibilities |
| signals.md | Discovery categories, interpretation, qualification and freshness |
| talk-track.md | Reviewed offer wording, support, limits and review date |
| voice.md | An approved source-backed writing sample |
| providers.yaml | Chosen CRM/email systems, capability mappings, canonical record mappings and completion rules |
| sources.json | Pinned source commit, watched files, exact quotes, attribution, limits and naming permission |
| approval.json | Application receipt binding the seven configuration files above |

`scripts/common.py` loads shared references and policy time. `scripts/evidence_gate.py` checks source receipts; `scripts/privacy_check.py` checks adoption disclosure; `scripts/provider_map.py` maps canonical and native fields; `scripts/readback_check.py` compares proposed and returned fields; `scripts/route_candidate.py` checks candidate routing. Workflow-specific tools remain in their workflow. Their docstrings own packet shapes and exit codes.

`../scripts/` contains setup, refresh, preflight and advisory style tools. Prospecting workflows never modify configuration. `../CONTEXT.md` owns output locations and human review boundaries.
