#!/usr/bin/env python3
"""Check ranked billing candidates and render exact configured template drafts.

Usage: python3 scripts/arr_growth_gate.py --packet FILE_OR_DASH [--shared DIR]
Use '-' for stdin with session-only private data. JSON stdout includes financial
amounts; do not save it unless the deployment's retention contract permits it.
Packet: {data_through_date: ISO date, rows: [row, ...]}.
Each row needs organization_id, organization_name, account_id, baseline_arr_usd,
current_arr_usd, net_change_usd, observed_dates, required_dates,
subscription_platform, billing_email, communications_enabled, last_touch_date,
daily_coverage_verified, mapping_verified, contacts_complete, activity_complete.
account: {id, exists, name, owner_id, owner_is_active, open_opportunity_ids,
          headcount, headcount_source}.
contacts: zero/one exact-email matches [{id, email, first_name}].
last_touch_date: most recent suppressing account-wide CRM/mail date or null only
after complete reads. Query and live-read receipts substantiate the true flags.

Checks adapter enabled, completed data date, coverage, finite consistent positive
ARR change, unique mapping, route, territory, billing permission, contact match,
suppression, rank and cap. The configured template's body/subject may not contain
amounts, percentages, digits or ARR language; the greeting is separately rendered.
No connectors or writes. Exit 0 selected candidates, 1 none, 2 unusable input.
"""
import argparse
import json
import re
import math
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import factory

HERE = Path(__file__).resolve().parent
SHARED = HERE.parent / "_shared"
sys.path.insert(0, str(HERE))
from route_candidate import load_rules, route, territory  # noqa: E402

FORBIDDEN = re.compile(r"[$%]|\bARR\b|\d")
ROW_KEYS = {"organization_id", "organization_name", "account_id", "baseline_arr_usd", "current_arr_usd",
            "net_change_usd", "observed_dates", "required_dates", "subscription_platform", "billing_email",
            "communications_enabled", "account", "contacts", "last_touch_date"}


def load_policy(shared=SHARED):
    return factory.read(shared / "policy.json")


def hold_reason(r, rules, pol, today):
    if type(r["observed_dates"]) is not int or type(r["required_dates"]) is not int or r["observed_dates"] != pol["window_days"] + 1 or r["required_dates"] != pol["window_days"] + 1 or r.get("daily_coverage_verified") is not True:
        return "incomplete_daily_coverage"
    if not all(type(r[k]) in (int, float) and math.isfinite(r[k]) for k in ("baseline_arr_usd", "current_arr_usd", "net_change_usd")):
        return "invalid_arr_values"
    if r["baseline_arr_usd"] < 0 or r["current_arr_usd"] < 0 or abs(r["current_arr_usd"] - r["baseline_arr_usd"] - r["net_change_usd"]) > 0.01:
        return "inconsistent_arr_values"
    if r["net_change_usd"] <= 0:
        return "no_positive_net_change"
    a = r["account"]
    if r.get("mapping_verified") is not True or a.get("id") != r["account_id"]:
        return "ambiguous_account_mapping"
    if r.get("activity_complete") is not True or r.get("contacts_complete") is not True:
        return "incomplete_live_reads"
    if not a.get("exists"):
        return "no_crm_account"
    if not isinstance(a.get("open_opportunity_ids"), list) or type(a.get("owner_is_active")) is not bool or not a.get("owner_id"):
        return "incomplete_live_reads"
    rt = route({"account_exists": True, "owner_id": a.get("owner_id"), "owner_is_active": a.get("owner_is_active"),
                "open_opportunity_ids": a["open_opportunity_ids"]}, rules)
    if rt != "scan":
        return rt
    t = territory(a.get("headcount"), rules)
    if t != "in":
        return f"territory_{t}"
    if not r["billing_email"]:
        return "billing_email_missing"
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", r["billing_email"]):
        return "billing_email_invalid"
    if r["subscription_platform"] not in pol["allowed_platforms"]:
        return "unsupported_billing_platform"
    if r["communications_enabled"] is not True:
        return "communications_disabled"
    if len(r["contacts"]) > 1:
        return "ambiguous_contact"
    for c in r["contacts"]:
        if (c.get("email") or "").lower() != r["billing_email"].lower():
            return "contact_email_mismatch"
    if r["last_touch_date"]:
        if date.fromisoformat(r["last_touch_date"]) >= today - timedelta(days=pol["suppression_days"]):
            return "suppressed_recent_touch"
    return None


def build_draft(r, pol):
    d = pol["email_template"]
    if not isinstance(d, dict):
        raise ValueError("approved email_template is unconfigured")
    first = r["contacts"][0].get("first_name") if r["contacts"] else None
    greeting = d["greeting_person"].format(first_name=first.strip()) if first and first.strip() \
        else d["greeting_team"].format(account_name=r["account"]["name"])
    body = d["body"].rstrip("\n")
    if FORBIDDEN.search(d["subject"]) or FORBIDDEN.search(body):
        raise ValueError("draft template contains a forbidden token")
    return {"to": r["billing_email"], "subject": d["subject"], "body": f"{greeting}\n\n{body}"}


def check(packet, policy, today=None, shared=SHARED):
    if not isinstance(packet, dict):
        raise ValueError("packet must be an object")
    pol = policy["arr_growth"]
    if pol["enabled"] is not True:
        return {"verdict": "block", "reasons": ["billing adapter disabled"]}
    rules = load_rules(shared)
    today = today or datetime.now(ZoneInfo(policy["identity"]["timezone"])).date()
    if date.fromisoformat(packet["data_through_date"]) != today - timedelta(days=pol["data_lag_days"]):
        return {"verdict": "block", "reasons": ["data_through_date is not the configured complete data date"]}
    rows = packet.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    selected, held = [], []
    if any(not isinstance(r, dict) for r in rows):
        raise ValueError("each billing row must be an object")
    account_counts = Counter(r.get("account_id") for r in rows)
    org_counts = Counter(r.get("organization_id") for r in rows)
    previous_growth = float("inf")
    for i, r in enumerate(rows, 1):
        missing = sorted(ROW_KEYS - set(r))
        if missing:
            raise ValueError(f"row {i} missing keys: {missing}")
        reason = hold_reason(r, rules, pol, today)
        if account_counts[r["account_id"]] > 1 or org_counts[r["organization_id"]] > 1:
            reason = "duplicate_account_mapping"
        if type(r["net_change_usd"]) in (int, float) and math.isfinite(r["net_change_usd"]):
            if r["net_change_usd"] > previous_growth:
                raise ValueError("billing rows must be ranked by descending net growth")
            previous_growth = r["net_change_usd"]
        entry = {"rank": i, "account_id": r["account_id"], "account_name": r["account"].get("name") or r["organization_name"],
                 "net_change_usd": r["net_change_usd"], "baseline_arr_usd": r["baseline_arr_usd"], "current_arr_usd": r["current_arr_usd"]}
        if reason:
            held.append({**entry, "hold": reason})
        elif len(selected) < pol["max_accounts"]:
            selected.append({**entry, "headcount": r["account"]["headcount"], "headcount_source": r["account"].get("headcount_source"),
                             "contact_id": r["contacts"][0]["id"] if r["contacts"] else None, "draft": build_draft(r, pol)})
        else:
            held.append({**entry, "hold": "over_max_accounts"})
    return {"verdict": "allow" if selected else "block", "data_through_date": packet.get("data_through_date"),
            "selected": selected, "held": held, "shortfall": max(0, pol["max_accounts"] - len(selected))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", required=True)
    ap.add_argument("--today", default=None)
    ap.add_argument("--shared", type=Path, default=SHARED)
    a = ap.parse_args()
    try:
        packet = json.loads(sys.stdin.read() if a.packet == "-" else Path(a.packet).read_text())
        policy = load_policy(a.shared)
        today = date.fromisoformat(a.today) if a.today else None
        out = check(packet, policy, today, a.shared)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(json.dumps({"verdict": "error", "reason": f"{type(e).__name__}: {e}"}, indent=2))
        return 2
    print(json.dumps(out, indent=2))
    return 0 if out["verdict"] == "allow" else 1


if __name__ == "__main__":
    sys.exit(main())
