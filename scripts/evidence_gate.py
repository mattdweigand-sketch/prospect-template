#!/usr/bin/env python3
"""Check one public-evidence receipt against the fetched page and emit the signal bundle.

Caller: signal-scan (one run per selected source).

    python3 scripts/evidence_gate.py --receipt receipt.json --page page.txt \
        --checked-at AWARE_FETCH_TIMESTAMP [--policy _shared/policy.json]

receipt.json
    {"account_name": str, "account_aliases": [str], "account_domain": str,
     "source_url": str, "published_date": "YYYY-MM-DD"|null, "quote": str,
     "evidence_subject": str, "signal_type": str, "quote_speaker": "account"|"third_party",
     "event_date": "YYYY-MM-DD" (required only when published_date is null)}
    published_date null means a live first-party page with no trustworthy publication date. The page must
    then name a dated event: event_date must appear in the page text in a common written form. Freshness is
    checked against event_date and the bundle carries published_date = event_date, date_basis "page_event".
    quote_speaker "account" means the account or a named alias said or wrote the quote. "third_party" means
    someone else (vendor, reporter) paraphrased them.

Checks. Required keys present. source_url is http(s). quote has at least policy scan.quote_min_words words
and appears verbatim in the page text (whitespace and curly quotes normalized). evidence_subject is
account_name or a declared alias. signal_type is a tier1 or tier2 web-source id in the taxonomy. The governing
date is not in the future and within freshness_days, using identity.timezone. Qualified bundles carry "warnings":
["third_party_paraphrase"] whenever quote_speaker is third_party, for any signal type.

Qualified bundles carry checked_on (validation date) and checked_at (actual source fetch timestamp with offset).
The CLI requires the fetch time explicitly or in receipt.checked_at; rechecking a saved file never refreshes it.
outreach_gate.py measures bundle age from checked_at.
For a deterministic replay, --now must be a full timezone-aware timestamp.

Exit 0 qualified, bundle JSON on stdout. Exit 1 no_usable_signal (never proof of absence).
Exit 2 unusable input. Always JSON on stdout, never a traceback.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import factory

REQUIRED = ("account_name", "account_aliases", "account_domain", "source_url",
            "published_date", "quote", "evidence_subject", "signal_type", "quote_speaker")
SPEAKERS = ("account", "third_party")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")


def date_forms(d):
    """Written forms of a date that a page may use. Case-insensitive match on the normalized page."""
    month = MONTHS[d.month - 1]
    forms = [d.isoformat(), f"{month} {d.day}, {d.year}", f"{month} {d.day} {d.year}", f"{d.day} {month} {d.year}",
             f"{month[:3]} {d.day}, {d.year}", f"{month[:3]}. {d.day}, {d.year}", f"{d.day} {month[:3]} {d.year}",
             f"{d.month}/{d.day}/{d.year}", f"{d.month:02d}/{d.day:02d}/{d.year}"]
    if month == "September":
        forms += [f"Sept {d.day}, {d.year}", f"Sept. {d.day}, {d.year}"]
    return forms


def normalize(text):
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def norm_name(name):
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def load_taxonomy(policy_path):
    """Load qualification rules, owner timezone and each signal's source boundary."""
    policy = json.loads(Path(policy_path).read_text())
    taxonomy = factory.taxonomy(Path(policy_path).parent)
    types = {}
    for tier, entries in taxonomy["tiers"].items():
        for entry in entries:
            types[entry["id"]] = {"tier": tier, "freshness_days": entry.get("freshness_days"),
                                  "source": entry.get("source")}
    return {**policy["scan"], "timezone": policy["identity"]["timezone"]}, types


def grade(receipt, page_text, scan_policy, types, today, checked_at=None):
    """checked_at is the timezone-aware moment the page was read. Defaults to now. outreach_gate.py measures elapsed time from it."""
    checked_at = checked_at or datetime.now().astimezone()
    if not isinstance(receipt, dict) or checked_at.tzinfo is None:
        return 2, {"outcome": "unusable", "reason": "object_and_aware_timestamp_required"}
    missing = [k for k in REQUIRED if k not in receipt]
    if missing:
        return 2, {"outcome": "unusable", "reason": "missing_keys", "keys": missing}
    if not isinstance(receipt["account_aliases"], list) or not receipt["account_aliases"] or any(not isinstance(v, str) or not v.strip() for v in receipt["account_aliases"]):
        return 2, {"outcome": "unusable", "reason": "account_aliases_not_list"}
    if any(not isinstance(receipt[k], str) or not receipt[k].strip() for k in REQUIRED if k not in ("account_aliases", "published_date")):
        return 2, {"outcome": "unusable", "reason": "nonempty_strings_required"}
    url = urlparse(receipt["source_url"])
    if url.scheme not in ("http", "https") or not url.hostname:
        return 2, {"outcome": "unusable", "reason": "source_url_not_http"}
    if receipt["quote_speaker"] not in SPEAKERS:
        return 2, {"outcome": "unusable", "reason": "quote_speaker_not_allowed", "allowed": list(SPEAKERS)}

    quote = normalize(receipt["quote"])
    if len(quote.split()) < scan_policy["quote_min_words"]:
        return 1, {"outcome": "no_usable_signal", "reason": "quote_too_short"}
    if quote not in normalize(page_text):
        return 1, {"outcome": "no_usable_signal", "reason": "quote_not_in_page"}

    owned = {norm_name(receipt["account_name"])} | {norm_name(a) for a in receipt["account_aliases"]}
    if norm_name(receipt["evidence_subject"]) not in owned:
        return 1, {"outcome": "no_usable_signal", "reason": "evidence_subject_not_account_owned",
                   "evidence_subject": receipt["evidence_subject"]}

    signal = types.get(receipt["signal_type"])
    if signal is None:
        return 2, {"outcome": "unusable", "reason": "signal_type_not_in_taxonomy"}
    if signal["tier"] not in ("tier1", "tier2"):
        return 1, {"outcome": "no_usable_signal", "reason": "tier3_never_qualifies"}
    if signal.get("source") != "web":
        return 1, {"outcome": "no_usable_signal", "reason": "signal_source_not_web"}

    if receipt["published_date"] is None:
        if receipt["quote_speaker"] != "account":
            return 1, {"outcome": "no_usable_signal", "reason": "event_fallback_requires_first_party"}
        domain = receipt["account_domain"].lower()
        if url.hostname.lower() != domain and not url.hostname.lower().endswith("." + domain):
            return 1, {"outcome": "no_usable_signal", "reason": "event_fallback_requires_account_host"}
        if not receipt.get("event_date"):
            return 1, {"outcome": "no_usable_signal", "reason": "undated_page_without_event_date"}
        date_field, date_basis = "event_date", "page_event"
    else:
        date_field, date_basis = "published_date", "published"
    try:
        governing = date.fromisoformat(receipt[date_field])
    except (ValueError, TypeError):
        return 2, {"outcome": "unusable", "reason": f"{date_field}_not_iso"}
    if governing > today:
        return 2, {"outcome": "unusable", "reason": f"{date_field}_in_future"}
    if date_basis == "page_event":
        page_norm = normalize(page_text).lower()
        if not any(f.lower() in page_norm for f in date_forms(governing)):
            return 1, {"outcome": "no_usable_signal", "reason": "event_date_not_in_page",
                       "event_date": receipt["event_date"]}
    age = (today - governing).days
    if age > signal["freshness_days"]:
        return 1, {"outcome": "no_usable_signal", "reason": "stale", "date_basis": date_basis,
                   "age_days": age, "freshness_days": signal["freshness_days"]}

    bundle = {k: receipt[k] for k in REQUIRED}
    bundle["event_date"] = receipt.get("event_date")
    bundle["published_date"] = governing.isoformat()
    bundle.update({"tier": signal["tier"], "date_basis": date_basis, "checked_on": today.isoformat(),
                   "checked_at": checked_at.isoformat(timespec="seconds"), "gate": "evidence_gate"})
    warnings = []
    if receipt["quote_speaker"] == "third_party":
        warnings.append("third_party_paraphrase")
    if warnings:
        bundle["warnings"] = warnings
    return 0, {"outcome": "qualified", "bundle": bundle}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--page", required=True)
    ap.add_argument("--policy", default=str(Path(__file__).resolve().parent.parent / "_shared" / "policy.json"))
    ap.add_argument("--now", help="Timezone-aware timestamp for deterministic replay; defaults to the current time")
    ap.add_argument("--checked-at", help="Actual timezone-aware page fetch time; otherwise receipt.checked_at is required")
    args = ap.parse_args()
    try:
        receipt = json.loads(Path(args.receipt).read_text())
        page_text = Path(args.page).read_text(errors="replace")
        scan_policy, types = load_taxonomy(args.policy)
        zone = ZoneInfo(scan_policy["timezone"])
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(zone)
        if now.tzinfo is None:
            raise ValueError("now must be a timezone-aware timestamp")
        today = now.astimezone(zone).date()
        raw_checked = args.checked_at or receipt.get("checked_at")
        if not isinstance(raw_checked, str):
            raise ValueError("record the actual source fetch time with --checked-at or receipt.checked_at")
        checked = datetime.fromisoformat(raw_checked.replace("Z", "+00:00"))
        if checked.tzinfo is None or checked > now:
            raise ValueError("checked_at must be timezone-aware and not in the future")
    except Exception as exc:  # bad input, never a traceback
        print(json.dumps({"outcome": "unusable", "reason": "input_error", "detail": str(exc)}))
        return 2
    try:
        code, payload = grade(receipt, page_text, scan_policy, types, today, checked_at=checked)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        code, payload = 2, {"outcome": "unusable", "reason": "input_error", "detail": str(exc)}
    print(json.dumps(payload, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
