# Portability and scope

This is an independently usable ICM template derived from the reviewed
prospect project, with seven canonical workflows. It is a new portable
implementation, not a byte-for-byte export or a validated deployment of the
original system's private helpers.

Preserved: workflow ownership, evidence attribution, exact action review,
fresh reads, provider readback, no sending email, and external systems of record.
Added for ICM: local editable review artifacts scoped to a task-supplied run ID.
These do not introduce a customer ledger or replace provider state.

Configuration: private identities, domain/owner IDs, CRM field names, quotas,
product claims, source repositories, schedules and collateral are absent.
The setup owns their local replacements. Example configuration is ignored
only after being copied to its deployment path; examples themselves are tracked.

Public-source research and CRM/mail workflows are portable once configured. Adoption and ARR growth require private-data adapters. The example claim is synthetic and unapproved. Claim refresh takes an explicitly configured knowledge source rather than a hard-coded private wiki.

The claim schema uses claim, limit and kind. There is no exact angle-copy rule. Matrix fit defaults to warn, preserving the reviewed deployment behavior; users may explicitly choose block. Both modes require an approved claim, source evidence and exact draft review.

Included checks cover repository structure, wrapper routes, local review
freshness and synthetic cases. They do not validate credentials, field mappings,
live provider writes, outreach meaning, or every original production helper.
Install and exercise required adapters before describing a deployment as operational.
