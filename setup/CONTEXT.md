# Configure the factory

Say **run setup** or invoke `prospect-setup` to follow the canonical
[guided workflow](../workflows/knowledge/prospect-setup.md). On an existing
deployment, show current settings and ask what to change.

Inputs: supplied ICP, messaging, proof and voice materials, or interview answers
using [questionnaire.md](questionnaire.md). Documents and connectors are optional
at interview start; unsupported claims remain gaps.
Process: bootstrap missing files through [installation.md](installation.md),
prepare mappings and sample emails, validate, then review exact changes.
Outputs: local policy.json, adapters.md, icp.md, taxonomy.json and claims.json;
private source evidence and run artifacts. pairings.md is generated.
Human check: review targeting, evidence, signal-to-claim fit, voice and exact
configuration. Provider readiness is verified separately before live effects.
Keep customer data, access tokens and run artifacts outside the public template.
