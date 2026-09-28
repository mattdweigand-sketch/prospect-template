# Executable tools

One home for Python implementation. Commands run from the repository root; each CLI's docstring and help define its inputs and exits.

| Tools | Job |
|---|---|
| `setup.py`, `validate_setup.py`, `source_snapshot.py`, `refresh_sources.py` | Stage, review and apply configuration or source updates |
| `preflight.py` | Check approved configuration and the selected workflow's dependencies |
| `route_candidate.py`, `evidence_gate.py`, `scan_verdict.py`, `privacy_check.py` | Check routing, evidence, report verdicts and adoption disclosure |
| `outreach_gate.py`, `arr_growth_gate.py`, `followup_gate.py`, `lint_draft.py` | Check proposals and advisory style |
| `provider_map.py`, `readback_check.py` | Map provider records and compare exact returned fields |
| `common.py`, `setup_common.py`, `policy_templates.py` | Shared configuration, path/hash and template helpers |
| `check_repo.py` | Verify layout, contracts, skill pointers and template neutrality |

## Inputs

Installed `../../.local/config/`, temporary synthetic or authorized packets, and the selected procedure. Production tools never fall back to `../../setup/templates/`.

## Output and human check

CLI JSON, local setup artifacts, or validation results as each tool declares. These scripts make no live provider writes. Run the relevant tests in `../tests/` and the repository verifier after changes; passing checks never replace the procedure's exact human approval.
