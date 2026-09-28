# Configurable CRM and email providers

`providers.yaml` declares the CRM and email system names, available tool capabilities, and record mappings. No provider is selected by default. Discover the tools and read their current schemas before configuring them. This repository supplies contracts and a local mapping helper, not installed connectors, credentials, or production adapters for every system. Setup can finish with unavailable capabilities left null; workflows stop before any step needing them.

Each capability has `tool`, `input_mapping`, `output_mapping`, `completion`, and `verification_reference`. Leave all five null when unavailable. Otherwise document exact argument names, query/filter syntax, associations, returned fields, pagination, async completion, and the schema or authorized read used to verify the mapping. `systems.crm` and `systems.email` name the chosen providers. Never infer access from a declared tool name.

| Capability | Required behavior |
|---|---|
| web.search / web.fetch | Discover pages and fetch full content with URL and capture time |
| crm.query | Read account, owner, open-deal, contact, task and meeting/event facts; complete every page |
| crm.create_account / update_owner / create_contact / create_task | Apply one exact approved proposal; retain returned native record ID |
| crm.readback | Retrieve every approved field and association from the resulting native record |
| email.search / email.read_message | Find messages in the requested scope; obtain complete recipients, content, aware timestamp and native sent-state evidence |
| email.create_draft / email.read_draft | Create an unsent draft and retrieve its full contents with the appropriate returned identifier |
| enrichment.verified_contact | Return a sourced, verified contact address and responsibility evidence |
| warehouse.query / status / results | Execute reviewed read-only queries with bound parameters; confirm success and retrieve complete results |

## Record mappings

Gates consume canonical JSON, independent of provider field names. `_shared/scripts/provider_map.py` owns the exact field sets in `CONTRACTS`. `providers.yaml` contains one null entry per record shape. Populate only the shapes needed by configured capabilities. Setup validation rejects incomplete mappings. Account/contact/task contracts include the relevant ownership and relationship fields; a system that cannot represent them cannot perform that workflow's write safely.

Each canonical field maps to a JSON pointer in a native record or payload:

```yaml
# An illustrative mapping fragment, not a production provider API schema.
owner_id:
  path: /properties/assigned_to
  convert: id_string
status:
  path: /properties/state
  values:
    - {from: waiting, to: Not Started}
    - {from: finished, to: Completed}
```

`read` maps native fields to canonical fields; `write` maps canonical fields to the native payload. Configure their directions separately. `path` supports nested objects and array positions. `convert` is `identity` by default; `id_string` explicitly converts an integer to a decimal string, and `integer` converts a canonical decimal string back without dropping leading zeros. `values` is an exact, type-sensitive lookup table. Unknown values fail. There are no implicit defaults, invented empty arrays, case folding of IDs, or fallback field names. Optional thread/message identifiers may be omitted from a mapping when the provider does not expose them.

```sh
python3 _shared/scripts/provider_map.py --record crm.task.write --input /tmp/task-proposal.json
python3 _shared/scripts/provider_map.py --record crm.task.read --input /tmp/native-task.json
```

Use a private temporary directory for real packets. Output on stdout is a mapping result, not a provider call or approval. The helper rejects missing fields, unknown enums, overlapping native write paths and unreviewed extra write fields. It handles structural mapping; connector envelopes, MIME, date representations and complex multi-call associations require an explicitly reviewed adapter step in the capability mapping. Keep those steps lossless and retain their source-call references. If they cannot be represented or verified, report the unsupported capability instead of guessing.

CRM IDs are opaque, case-sensitive strings. Normalize numeric IDs only with a declared conversion. Preserve account/contact/owner association semantics even if the provider calls them companies, people, activities or another name. The gate's `account_id` and `contact_id` must resolve to those actual objects. Query open deals separately and form `open_deal_ids` only after a complete native read; never replace missing results with an empty list. Verify `policy.crm.open_deal`, native task statuses and `policy.outreach.task_status_map` for this installation.

Activity rows use `kind: task | event | email_sent`, a date, and `who` with `who_kind: contact_id | email` when known. Email addresses compare case-insensitively; opaque IDs compare exactly. Unknown targets are null and suppress conservatively. Multi-recipient events must yield a row per target, with an unknown row if any target cannot be resolved. Do not collapse a list into an invented ID.

## Query and completeness semantics

Read intents are structured data, not executable query text. Map account relationships, recipient/domain scope and inclusive time boundaries to the configured provider's filters. Bind parameters through its supported interface. Do not interpolate opaque IDs into a query. Fetch every page; if a native filter is coarser, fetch a complete superset then apply the exact intent locally. If completeness cannot be established, stop. Missing, failed, stale, denied or truncated reads are unknown; only completed native reads establish zero results.

For prospector, preflight separately lists conditional write and enrichment capabilities. A sourced existing contact does not require enrichment. Missing create or ownership-update support prevents that branch without blocking research results.

## Exact proposals and readback

Before each external write, re-read ownership, open deals, contact, suppression and duplicate state as applicable, then rerun the gate. Map its canonical proposal into a concrete native payload. Review both the human-readable values and the native fields, target, associations, identifiers and any required transport envelope before asking for approval. Any mapping, field or state change requires a new proposal.

After writing, retain returned IDs and query the actual record. Normalize only returned values with the configured read mapping. Run `_shared/scripts/readback_check.py` against the approved canonical fields. Also compare approved native fields/envelope semantics that are outside the canonical shape. Never reconstruct a readback value from the proposal. Creation success alone is insufficient. Stop and report mismatches; reconcile ambiguous timeouts before any retry.

For email, approve one `to`, exact `subject` and complete `body`, with `cc: []` and `bcc: []`. A provider may use MIME, recipient objects, HTML or a flat body: use its discovered schema and lossless encoding/decoding. Read every recipient header, full body and multipart alternative; previews do not suffice. The native draft ID and underlying message ID may differ; use the identifier the retrieval capability actually requires. Do not assume thread support or a particular tool argument name. The normalized full readback must explicitly include empty `cc` and `bcc`; missing recipient coverage stops. Run `readback_check.py --email`. Signatures, extra recipients and body transformations are mismatches. Never invoke send, reply or forward.

Follow-up requires one native sent message with `is_sent: true`, a message ID, recipient, subject and aware timestamp. Map sent state from actual provider folder/status/labels and inspect its native evidence; do not set it from a draft or a user's recollection. `thread_id` is optional. These packet checks cannot authenticate a provider return or prove human consent.

## Optional warehouse modules

Read `setup/subscription-interface.md` before enabling adoption or ARR. They require reviewed private queries, unambiguous account-to-organization mapping, daily subscription state and complete coverage. ARR additionally requires upstream USD normalization under reviewed FX/date/calculation rules and an explicit USD currency field in each result row. Adoption exposes only the allowed aggregate bundle; ARR and billing-source details stay internal. Public signals do not require a warehouse.
