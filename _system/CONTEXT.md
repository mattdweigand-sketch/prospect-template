# Workspace maintenance

Implementation and verification live here so the working folders contain only their contracts and procedures.

| Folder or file | Owns |
|---|---|
| `scripts/CONTEXT.md` | Setup tools, runtime gates, shared helpers and repository verification |
| `queries/CONTEXT.md` | Fictional SQL interfaces for optional warehouse branches |
| `tests/CONTEXT.md` | Synthetic regression suite |
| `history/CONTEXT.md` | Build and design history |
| `requirements.txt` | Python dependencies |

## Inputs

The changed contract or script, its callers and the affected tests. Use `../AGENTS.md` to find the owning workflow; do not load every workflow for an unrelated change.

## Process

Run commands from the repository root with the installed Python environment:

```sh
python3 -m unittest discover -s _system/tests
python3 _system/scripts/check_repo.py
```

## Output and human check

Review the diff and verification results before publishing. Tests use synthetic data; they do not establish source truth, actual approval or live provider compatibility. Keep scratch work outside the checkout and private deployment files under `../.local/`.
