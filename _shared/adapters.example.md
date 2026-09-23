---
type: adapter-configuration
status: unconfigured
---
# Adapter configuration

Copy to adapters.md and fill only the adapters needed by a workflow.
No credentials belong in this file. An adapter is a mapping to tools the host
already exposes; this repository does not ship an authenticated connector.

## CRM
Provider and tools: unconfigured.
Identity lookup; account/domain resolution; owner and open-deal query: unconfigured.
Contact, Task, Event and Opportunity field mapping: unconfigured.
Stable record URLs, pagination and complete-result indication: unconfigured.
Allowed write operations and fresh-read/readback tools: unconfigured.
Validation messages, task duplication keys and note history format: unconfigured.

## Mail and calendar
Search, paging, sent-message proof, read-message and calendar tools: unconfigured.
Draft creation, draft identity lookup and independent readback: unconfigured.
Internal domains come from policy.identity; do not repeat them here.

## Optional capabilities
Verified professional contact enrichment; aggregate adoption lookup; billing growth query with complete daily snapshots and permitted recipients; versioned knowledge source reads.
Each enabled adapter must name its tool, input mapping, output fields,
completeness criteria, permitted audience and verification read. Keep disabled
capabilities unavailable until configured and tested with synthetic data.
