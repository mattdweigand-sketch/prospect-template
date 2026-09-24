#!/usr/bin/env python3
"""Emit the verdict and Next line for one signal-scan run. signal-scan copies both verbatim.

Usage:
    python3 scripts/scan_verdict.py <gate_output.json> [<gate_output.json> ...]

Arguments are evidence_gate.py outputs in report order. Position is the report's signal number
(the first file is Signal 1). Each file is {"outcome": "qualified", "bundle": {...}} or a
no_usable_signal / unusable output. Declared failures need a reason and remain coverage limitations.
Qualified bundles must have the complete evidence-gate shape and canonical governing date.
Malformed envelopes never count as checked evidence. Taxonomy membership belongs to evidence_gate.

Rule, in code so no run can add a bar. Any qualified signal on an owned account is a reason to
reach out. Recommended signal is the newest tier1, else the newest tier2, ties to the lower number.
Taxonomy admission (1 tier1 or 2 tier2) belongs to signal-prospector and route_candidate.py only.

A fit rejection is not made here. The report names it per item as "Rejected on fit, <reason>" and
the verdict line stays as emitted.

Exit 0 verdict JSON on stdout. Exit 2 unusable input. Never a traceback.
"""
import json
import sys
from datetime import date, datetime
from urllib.parse import urlparse

import factory

TIER_ORDER = {"tier1": 0, "tier2": 1}


def load(paths):
    outs = []
    for p in paths:
        try:
            with open(p) as fh:
                outs.append(json.load(fh))
        except (OSError, UnicodeError, json.JSONDecodeError) as e:
            return None, {"outcome": "unusable", "reason": "unreadable_gate_output", "path": p, "detail": str(e)}
    return outs, None


def verdict(outs):
    qualified = []
    for n, o in enumerate(outs, start=1):
        if not isinstance(o, dict) or o.get("outcome") not in ("qualified", "no_usable_signal", "unusable"):
            return {"outcome": "unusable", "reason": "invalid_gate_output", "signal": n}
        if o["outcome"] != "qualified":
            if not factory.nonblank(o.get("reason")):
                return {"outcome": "unusable", "reason": "missing_gate_reason", "signal": n}
            continue
        b = o.get("bundle")
        try:
            validate_bundle(b)
        except (ValueError, TypeError, KeyError) as exc:
            return {"outcome": "unusable", "reason": "invalid_qualified_bundle", "signal": n, "detail": str(exc)}
        qualified.append({"signal": n, "signal_type": b["signal_type"], "tier": b["tier"],
                          "published_date": b["published_date"]})
    checked = len(outs)
    if not qualified:
        return {"checked": checked, "qualified": [], "recommended": None,
                "verdict": "Nothing qualified. Not proof of absence.",
                "next": "Stop"}
    rec = min(qualified, key=lambda q: (TIER_ORDER[q["tier"]], -date.fromisoformat(q["published_date"]).toordinal(), q["signal"]))
    return {"checked": checked, "qualified": qualified, "recommended": rec["signal"],
            "verdict": f"Signal {rec['signal']} qualified.",
            "next": f"signal-outreach with Signal {rec['signal']}"}


def validate_bundle(bundle):
    """Validate the evidence output shape; taxonomy membership belongs to its gate."""
    factory.require(isinstance(bundle, dict), "bundle must be an object")
    strings = ("account_name", "account_domain", "source_url", "quote", "evidence_subject", "signal_type", "tier",
               "published_date", "date_basis", "checked_on", "checked_at", "quote_speaker", "gate")
    factory.require(all(factory.nonblank(bundle.get(k)) for k in strings), "qualified bundle is missing nonblank string fields")
    aliases = bundle.get("account_aliases")
    factory.require(isinstance(aliases, list) and bool(aliases) and all(factory.nonblank(a) for a in aliases), "account_aliases must be nonblank strings")
    factory.require(bundle["tier"] in TIER_ORDER and bundle["gate"] == "evidence_gate", "invalid tier or gate")
    factory.require(bundle["quote_speaker"] in ("account", "third_party") and bundle["date_basis"] in ("published", "page_event"), "invalid quote speaker or date basis")
    url = urlparse(bundle["source_url"])
    factory.require(url.scheme in ("http", "https") and bool(url.hostname), "source_url must be HTTP(S)")
    for key in ("published_date", "checked_on"):
        factory.require(date.fromisoformat(bundle[key]).isoformat() == bundle[key], key + " must be canonical YYYY-MM-DD")
    checked = datetime.fromisoformat(bundle["checked_at"].replace("Z", "+00:00"))
    factory.require(checked.tzinfo is not None, "checked_at must be timezone-aware")
    factory.require("event_date" in bundle, "event_date must be present or null")
    if bundle["event_date"] is not None:
        factory.require(isinstance(bundle["event_date"], str) and date.fromisoformat(bundle["event_date"]).isoformat() == bundle["event_date"], "event_date must be canonical YYYY-MM-DD")
    if bundle["date_basis"] == "page_event":
        factory.require(bundle["event_date"] == bundle["published_date"], "event fallback date must match published_date")


def main(argv):
    if not argv:
        print(json.dumps({"outcome": "unusable", "reason": "no_gate_outputs"}))
        return 2
    outs, err = load(argv)
    if err:
        print(json.dumps(err))
        return 2
    v = verdict(outs)
    print(json.dumps(v, indent=1))
    return 2 if v.get("outcome") == "unusable" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
