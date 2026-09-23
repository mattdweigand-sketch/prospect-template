# Active run

This folder holds one task, copied from the repository's _templates/run/.
Read repository-root workflows/run.md and the workflow named in request.md.

Inputs: request.md and the exact source references it names.
Process: prepare 01_review.md, obtain human review, then record approved results.
Outputs: 01_review.md, review.json, 02_result.json.
Human check: inspect the review and its revision before any approved effects.
These local files are review surfaces, not a replacement for CRM or sent mail.
