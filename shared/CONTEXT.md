# Shared provider and data contracts

Stable references used by more than one workflow. Load only the contract required by the selected procedure.

| Reference | Scope |
|---|---|
| `providers.md` | Tool discovery, provider mappings, complete reads and exact native readback |
| `subscription-interface.md` | Optional adoption and ARR data definitions, privacy and USD normalization |

Installed business settings live in `../.local/config/`; their seven-file schema is described in `../setup/templates/CONTEXT.md`. Shared checks live in `../_system/scripts/`. This folder contains no customer data or executable tools.

Review changes to these contracts against their affected procedures and tests. `../CONTEXT.md` owns review, output locations and state boundaries.
