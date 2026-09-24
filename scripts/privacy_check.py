#!/usr/bin/env python3
"""Privacy check for the signal-user-scan adoption bundle.

Usage: python3 privacy_check.py --bundle <bundle.json> [--policy <policy.json>]

Reads the allowed key list and key types from policy.json `adoption.bundle_keys`.
Fails when the bundle has a key outside that list, a value of the wrong type,
or any string that looks like an email address or a person's activity timestamp.
Prints the verdict JSON to stdout.

Exit codes: 0 clean, 1 blocked, 2 usage or input error.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from datetime import date

HERE = Path(__file__).resolve().parent
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
TYPES = {"str": str, "bool": bool, "int": int, "list": list}


def load_policy(path):
    allowed = json.loads(path.read_text())["adoption"]["bundle_keys"]
    if not isinstance(allowed, dict):
        raise ValueError("adoption.bundle_keys must be an object")
    return allowed


def check(bundle, allowed):
    if not isinstance(bundle, dict) or not isinstance(allowed, dict) or not allowed or any(t not in TYPES for t in allowed.values()):
        raise ValueError("bundle and allowed key types must be configured objects")
    problems = []
    for k in bundle:
        if k not in allowed:
            problems.append(f"forbidden key: {k}")
    for k, typ in allowed.items():
        if k not in bundle:
            problems.append(f"missing key: {k}")
        elif not isinstance(bundle[k], TYPES[typ]) or (typ == "int" and isinstance(bundle[k], bool)):
            problems.append(f"wrong type for {k}: expected {typ}")
    for k, v in bundle.items():
        texts = v if isinstance(v, list) else [v]
        for t in texts:
            if isinstance(v, list) and not isinstance(t, str):
                problems.append(f"non-string category in {k}")
            if isinstance(t, str):
                if EMAIL_RE.search(t):
                    problems.append(f"email address in {k}")
                if TIMESTAMP_RE.search(t):
                    problems.append(f"timestamp in {k}")
    if isinstance(bundle.get("data_through_date"), str):
        try:
            date.fromisoformat(bundle["data_through_date"])
        except ValueError:
            problems.append("invalid data_through_date")
    if type(bundle.get("mapped_org_count")) is int and bundle["mapped_org_count"] < 0:
        problems.append("mapped_org_count must be nonnegative")
    if "adoption" in allowed and bundle.get("adoption") not in ("org_adopted", "individuals_only", "none_found", "unknown"):
        problems.append("invalid adoption category")
    if all(type(bundle.get(k)) is bool for k in ("org_subscribed", "paid_individuals_exist")):
        derived = "org_adopted" if bundle["org_subscribed"] else "individuals_only" if bundle["paid_individuals_exist"] else "none_found"
        if bundle.get("adoption") not in (derived, "unknown"):
            problems.append("adoption category contradicts aggregate facts")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--policy", default=str(HERE.parent / "_shared" / "policy.json"))
    a = ap.parse_args()
    try:
        bundle = json.loads(Path(a.bundle).read_text())
        allowed = load_policy(Path(a.policy))
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(json.dumps({"verdict": "error", "reason": str(e)}))
        return 2
    if not allowed or not isinstance(bundle, dict):
        print(json.dumps({"verdict": "error", "reason": "policy has no adoption.bundle_keys or bundle is not an object"}))
        return 2
    try:
        problems = check(bundle, allowed)
    except (ValueError, TypeError, KeyError) as e:
        print(json.dumps({"verdict": "error", "reason": str(e)}))
        return 2
    print(json.dumps({"verdict": "clean" if not problems else "blocked", "problems": problems}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
