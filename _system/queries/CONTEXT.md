# Optional warehouse interfaces

These SQL files describe fictional source views. They cannot be used directly against a live warehouse.

| Query | Consumer |
|---|---|
| `adoption_territory.sql` | Account discovery |
| `adoption_lookup.sql` | Account adoption lookup |
| `arr_growth_source.sql` | Self-serve ARR growth |

## Inputs

Read `../../shared/subscription-interface.md`, the chosen workflow contract and the query header for parameter order, permitted fields and data meaning.

## Output and human check

Setup creates a reviewed private mapping in `../../.local/queries/` and binds its hash in policy. Review schema, privacy, daily coverage, USD/FX rules where relevant and authorized read-only compatibility results. No production query or customer data is stored here.
