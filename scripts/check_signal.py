#!/usr/bin/env python3
"""Check source-quote structure and dates; semantic qualification remains a human review."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse


def normalize(text):
    return " ".join(text.split()).casefold()


def check(bundle, page, taxonomy, now):
    errors, warnings = [], []
    required = ("account_name", "account_domain", "account_aliases", "signal_type", "source_url",
                "quote", "quote_speaker", "evidence_subject", "published_date", "event_date", "checked_at")
    if not isinstance(bundle, dict) or any(k not in bundle for k in required):
        return ["bundle is missing required fields"], warnings
    strings = [k for k in required if k not in ("account_aliases", "published_date", "event_date")]
    if any(not isinstance(bundle[k], str) or not bundle[k].strip() for k in strings):
        return ["bundle string fields must be nonempty"], warnings
    aliases = bundle["account_aliases"]
    if not isinstance(aliases, list) or not aliases or any(not isinstance(a, str) or not a.strip() for a in aliases):
        return ["account_aliases must be a nonempty string list"], warnings
    if normalize(bundle["evidence_subject"]) not in [normalize(a) for a in aliases]:
        errors.append("evidence subject is not a declared account alias")
    if bundle["quote_speaker"] not in ("account", "third_party"):
        errors.append("quote_speaker must be account or third_party")
    if bundle["quote_speaker"] == "third_party":
        warnings.append("third-party attribution needs explicit semantic review")
    quote = bundle["quote"]
    if len(quote.split()) < 5 or normalize(quote) not in normalize(page):
        errors.append("quote must have at least five words and occur in the fetched page")
    url = urlparse(bundle["source_url"])
    if url.scheme not in ("http", "https") or not url.hostname:
        errors.append("source_url must identify an HTTP(S) source page")
    signals = taxonomy.get("signals", [])
    matches = [row for row in signals if row.get("id") == bundle["signal_type"]]
    if len(matches) != 1 or matches[0].get("tier") not in (1, 2):
        errors.append("signal_type must match one tier1 or tier2 taxonomy row")
    try:
        checked = datetime.fromisoformat(bundle["checked_at"].replace("Z", "+00:00"))
        if checked.tzinfo is None or now.tzinfo is None:
            raise ValueError("timezone required")
        if checked > now:
            errors.append("checked_at is in the future")
    except ValueError:
        errors.append("checked_at must be a timestamp with timezone offset")
    try:
        published = bundle["published_date"]
        event = bundle["event_date"]
        chosen = published or event
        occurred = date.fromisoformat(chosen)
        if not published and (event not in page or bundle["quote_speaker"] != "account"):
            errors.append("event-date fallback needs that date on a first-party page")
        age = (now.date() - occurred).days
        if age < 0:
            errors.append("source event or publication date is in the future")
        if len(matches) == 1 and age > matches[0]["freshness_days"]:
            errors.append("source is outside the taxonomy freshness window")
    except (ValueError, TypeError, KeyError):
        errors.append("a valid publication date or explicit source event date is required")
    return errors, warnings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--page", required=True)
    parser.add_argument("--taxonomy", default="_shared/taxonomy.json")
    parser.add_argument("--now")
    args = parser.parse_args()
    try:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
        errors, warnings = check(json.loads(Path(args.bundle).read_text()), Path(args.page).read_text(),
                                 json.loads(Path(args.taxonomy).read_text()), now)
        print(json.dumps({"structural_checks_passed": not errors, "errors": errors, "warnings": warnings,
                          "semantic_qualification": "requires review"}, indent=2))
        sys.exit(bool(errors))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"structural_checks_passed": False, "error": str(exc)}))
        sys.exit(2)
