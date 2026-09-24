# Synthetic verification

Inputs: canonical workflows/helpers and synthetic fixtures in gate_fixtures.py.
Never load a deployment's private factory or a live service.
Process: run `python3 -B -m unittest discover -s tests -v`. Each gate has a
matching test module; test_safety_boundaries.py covers cross-workflow constraints
and pinned source reads. test_workflow.py covers routing and the review lifecycle.
Outputs: test results on stdout; temporary synthetic files/repositories cleaned
by tests. No CRM/mail/warehouse effects. Helper CLI tests use temporary --shared.
Human check: read failures against the owning workflow's requirements. Tests
validate mechanics, not semantic truth, human consent or live adapter mappings.
