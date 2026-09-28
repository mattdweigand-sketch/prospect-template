# Starter business configuration

These seven files are fictional setup inputs and the schema examples used by the validator. Setup copies them into a private proposal; they cannot authorize live work.

| File | Owns |
|---|---|
| `policy.yaml` | Identity, limits, optional modules, retention and approval boundaries |
| `icp.md` | Companies, territory and buyer responsibilities |
| `signals.md` | Signal definitions, qualification and freshness |
| `talk-track.md` | Supported messaging and its review date |
| `voice.md` | Writing sample |
| `providers.yaml` | Configurable CRM/email capabilities and record mappings |
| `sources.json` | Pinned sources, quotations, attribution and claim limits |

## Process and output

Follow `../procedure.md` to populate and review a complete proposal. Approved settings live in `../../.local/config/`; its generated `approval.json` binds the seven installed files. On updates, setup copies the active settings instead of resetting to these examples.

## Human check

Review business meaning, evidence, voice, provider mappings and exact proposed bytes. Keep these reusable starters fictional and optional subscription modules disabled.
