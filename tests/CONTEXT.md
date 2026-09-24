# Synthetic verification

Inputs: canonical workflows/helpers and synthetic fixtures in gate_fixtures.py.
Never load a deployment's private factory or a live service.
Process: run `python3 -B -m unittest discover -s tests -v`. Each gate has a
matching test module; test_safety_boundaries.py covers cross-workflow constraints
and pinned source reads. test_workflow.py covers routing and the review lifecycle.
test_run_checks.py covers required inputs, recomputed gate results and reviewed handoffs.
test_end_to_end.py installs the public template into a temporary workspace and
exercises all seven CLI workflows with synthetic provider evidence. It covers
source refresh, review/apply/recovery and scan-to-outreach-to-follow-up handoffs.
test_setup.py covers software and commercial-service configurations, private source intake,
configuration readiness, mapping boundaries and reviewed setup updates. Sample
claim choices are explicit fixtures; semantic selection remains human-reviewed.
Outreach tests exercise explicit provider status mappings and fail on unknown
states. Refresh tests reject malformed contradiction registers and match full
source paths, including when two files share a basename.
Outputs: test results on stdout; temporary synthetic files/repositories cleaned
by tests. No CRM/mail/warehouse effects. Helper CLI tests use temporary --shared.
Human check: read failures against the owning workflow's requirements. Tests
validate mechanics, not semantic truth, human consent or live adapter mappings.
