# Synthetic regression tests

Tests exercise setup/application, provider record mappings, workflow gates, SQL contracts, skill pointers and repository layout. `_support.py` creates temporary fictional configuration and explicitly selects it for tests.

## Inputs

Implementation in `../scripts/`, SQL in `../queries/`, starter files in `../../setup/templates/` and synthetic fixtures defined in each test.

## Process

From the repository root, run `python3 -m unittest discover -s _system/tests` with the installed environment. Fixtures and setup rehearsals use temporary directories.

## Output and human check

Review failures and test summaries. Tests do not call live providers, authenticate source meaning, prove human approval or certify a warehouse schema. Keep test files here so ordinary workflow folders remain readable.
