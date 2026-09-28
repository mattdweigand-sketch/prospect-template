# Optional subscription-data interface

This module fits businesses with individual and organization subscriptions and recurring revenue. Keep it disabled for offers without that model. No specific software product, billing provider or production schema is assumed.

The three bundled SQL files use Snowflake-style syntax against fictional `prospect_source` views. These views do not exist until an operator maps or rewrites the queries for the actual warehouse. Do not execute them directly. A different SQL dialect requires translation and validation, not a provider-name substitution.

| Fictional view | Required source meaning |
|---|---|
| account | CRM Account id, name, owner id, employee count, website and deletion state |
| user_domains | User id and permitted normalized business email domain; identifiers never leave the query |
| paid_individual_subscription_daily | User id, snapshot_date and whether an individual subscription is paying |
| organizations | Organization id, deletion state, service type, permitted billing_email and outreach_permitted |
| organization_account_map | Unambiguous organization-to-CRM-Account mapping |
| organization_subscription_daily | Organization id/name, snapshot_date, subscription/payment state, platform and annual_recurring_revenue |

`snapshot_date` follows the configured business reporting timezone. `billing_email` is a permitted business billing contact from the configured billing system. `outreach_permitted` must have a reviewed meaning; a similarly named product flag is not automatically outreach consent. Annual recurring revenue must use a consistent currency and calculation, and every day in the configured window must be present exactly once.

Setup maps the actual data definitions, query bindings, allowed output fields and privacy restrictions. Save only reviewed private query copies under `.local/queries/` and bind their hashes in policy. The application-level output fields and ownership checks still target the supported CRM workflow. Missing or ambiguous mappings block the optional module; they never weaken the basic public-signal checks.
