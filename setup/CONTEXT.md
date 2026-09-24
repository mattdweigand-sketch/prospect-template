# Configure the factory

Inputs: [questionnaire.md](questionnaire.md), _shared/policy.example.json and _shared/adapters.example.md.
Process: follow [installation.md](installation.md), collect only missing answers,
and write local configuration in the owning files. Existing setup is edited by diff.
Outputs: _shared/policy.json and _shared/adapters.md; Prospect also uses local icp.md, taxonomy.json and claims.json.
Human check: review configuration, connector access and one synthetic run before live effects.
Do not copy customer data, access tokens or prior-run artifacts into the public template.
Installation covers configuration, required adapters and validation. The
[questionnaire](questionnaire.md) routes each answer to its owning file.
