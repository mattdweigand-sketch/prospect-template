# Native provider contracts

`providers.yaml` maps capabilities to the tools actually available in this Codex session. Discover the tools and read their schemas before configuring or calling them. The template ships no credentials, connector IDs or assumed MCP server. A configured tool name is not proof of installation, authentication, scope or data access. Preflight reports mapping readiness; actual reads establish runtime availability.

Each capability has `tool`, `input_mapping`, `output_mapping`, `completion`, and `verification_reference`. Leave all values null when unavailable. Record exact argument names, native returned fields, pagination/async completion rules and the tool-schema or authorized test reference. Capabilities may map to the same provider tool.

| Capability | Required behavior |
|---|---|
| web.search / web.fetch | Discover pages and obtain full source content with URL and capture time; a snippet cannot substitute for a page |
| salesforce.query | Read Account, Owner, Opportunity, Contact, Task and Event fields used by the selected procedure; complete all pages |
| salesforce.create_account / update_owner / create_contact / create_task | Write only exact approved fields, one record per proposal; retain native record Id |
| salesforce.readback | Query the returned record Id with every approved field; preserve native values |
| gmail.search / gmail.read_message | Search complete relevant sent history, then read native message headers, labels, recipients, body and timestamp; a draft is not proof of sending |
| gmail.create_draft / gmail.read_draft | Create an unsent draft from approved fields, retain draft and message identifiers, then obtain complete native content |
| enrichment.verified_contact | Return a sourced, verified contact email and responsibility evidence; never generate an address |
| warehouse.query / status / results | Bind reviewed query parameters, execute read-only, wait for confirmed success, retrieve complete results and detect truncation |

For prospector, preflight requires research and CRM reads and separately lists missing conditional claim-write or enrichment capabilities. Check the capability before entering that branch; a sourced existing Contact does not require an enrichment fallback. Missing write capability prevents that write.

Before reads, verify the Account/recipient scope and requested date window. Missing, denied, failed, stale, paginated-incomplete or truncated reads are unknown. Only a completed native read may establish zero rows. Record native call references in the chat and in the gate receipt fields where required. Status maps must reflect this Salesforce installation; unknown values stop.

Before each external write, re-read the relevant ownership, open Opportunity, contact, suppression or duplicate state. Re-run the applicable gate; changed facts or fields require a new exact proposal. Never retry a write after an ambiguous timeout until a native lookup establishes whether it occurred. A successful create return is not complete readback.

## Gmail details

The native connector may take a MIME `message` tree rather than a flat recipient/body object. Read its schema: map approved To and Subject headers and the exact plain-text body to the supported structure. Do not add a signature, tracking content, alternate recipient or body transformation after approval. Keep CC and BCC empty. Preserve both native draft Id and underlying message Id when returned. A tool named `read_email` commonly requires `message_id`; pass the returned message Id, not the draft Id. Other connectors may expose a draft-specific retrieval method: follow that schema.

Extract `to`, `subject`, `body`, `cc`, and `bcc` from the native read response, decoding its declared MIME/encoding. Use all returned recipient headers and check multipart alternatives for conflicting text. A missing full body or missing complete recipient view is an incomplete readback. If a tool only returns a preview or simplified summary, use a full-message retrieval capability; otherwise stop and report the limitation. Do not reconstruct any readback value from the proposal.

Run `_shared/scripts/readback_check.py --gmail` on the approved fields and the normalized native values. Keep normalization limited to lossless decoding and structural field mapping; whitespace, signature, recipient or content changes are mismatches. The checker rejects added CC/BCC. It does not decode MIME itself or authenticate the tool response. Stop on mismatch and report it without silently repairing the draft. Never invoke send, reply or forward.

## Optional warehouse modules

The query interfaces assume unambiguous Account-to-organization mapping, deleted-record filtering, daily subscription state and (for ARR) complete 31-day coverage of a 30-day change. Setup must verify these semantics against the actual warehouse. Adoption reports only the allowed aggregate bundle; never expose individual identities, counts, query content or activity timing. ARR and billing-source details remain internal. Public signal-only workflows do not require a warehouse.
