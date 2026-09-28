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
| organization_subscription_daily | Organization id/name, snapshot_date, subscription/payment state, platform, annual_recurring_revenue normalized to USD and currency (`USD`) |

`snapshot_date` follows the configured business reporting timezone. `billing_email` is a permitted business billing contact from the configured billing system. `outreach_permitted` must have a reviewed meaning; a similarly named product flag is not automatically outreach consent. Annual recurring revenue must already be normalized to **USD** using a consistent calculation; every day in the configured window must be present exactly once. The SQL performs no currency conversion. Its daily `currency` field must be `USD`; any other or missing currency drops the organization from the result. Query results explicitly carry `currency: USD`, and the gate rejects missing/non-USD units before evaluating growth.

For non-USD billing, the reviewed private mapping must specify the original units, FX rate source, effective date, whether rates are held constant or vary by snapshot, rounding and annualization rules. Apply that conversion upstream of the query. Document whether currency movements can count as growth and review that business meaning. Do not relabel native EUR or another currency as USD. A reported USD label and consistent arithmetic do not authenticate the underlying rates or prove conversion occurred.

Setup maps the actual data definitions, query bindings, allowed output fields and privacy restrictions. Save only reviewed private query copies under `.local/queries/` and bind their hashes in policy. The application-level output fields and ownership checks still target the supported CRM workflow. Missing or ambiguous mappings block the optional module; they never weaken the basic public-signal checks.
