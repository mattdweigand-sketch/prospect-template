# Run starters

Input: one task-supplied run ID and a routed command.
Process: scripts/runs.py init copies [run/](run/CONTEXT.md) without overwriting a run.
Outputs: ignored output/{run-id}/ with editable request, review, review record and result.
Human check: fill the scope and read the review before recording an actual approval.
Templates are blank structure; their presence never counts as completed work.
