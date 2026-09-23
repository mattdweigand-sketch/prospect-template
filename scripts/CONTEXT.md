# Local tooling

Inputs: scripts/wrapper-contract.json, canonical workflow paths, and the explicitly selected local run.
Process and ownership:

| Tool | Job |
|---|---|
| wrappers.py | Generate/check root and family task maps, .agents skill pointers and .claude command pointers |
| runs.py | Copy a run starter, record an existing review reference, inspect local run state |
| check_signal.py | Check a fetched page quote, declared attribution, timezone timestamp and taxonomy freshness; semantic qualification stays human |
| check_repo.py | Check links, contract shape, wrapper parity and public-template hygiene |

Outputs: generated wrappers or output/{run-id}/ artifacts, according to the invoked command.
Human check: review the diff; a passing static check does not approve external actions.
Run `python3 scripts/check_repo.py` and `python3 -m unittest discover -s tests -v`.
The tools use Python 3.9+ standard library and make no network requests.

Signal bundle fields: account_name, account_domain, account_aliases (nonempty
list), signal_type, source_url, quote, quote_speaker (account or third_party),
evidence_subject, published_date (ISO date or null), event_date (ISO date or
null), checked_at (ISO timestamp with offset). The declaring agent must check
that aliases belong to the account. Source dates come from the fetched page.
Run `python3 scripts/check_signal.py --bundle output/RUN_ID/bundle.json --page output/RUN_ID/source.txt`.
The fetched source text and bundle belong in that review's artifacts list.
