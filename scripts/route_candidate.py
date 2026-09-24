#!/usr/bin/env python3
"""Admit and route one prospecting candidate. No provider calls or writes.

Usage: python3 scripts/route_candidate.py --receipt FILE [--shared DIR]
Receipt required keys: domain (normalized host), headcount (verified nonnegative
integer or null), signals [{signal_type, tier: tier1|tier2|tier3}], account_exists
(boolean), owner_id (string or null), owner_is_active (boolean or null),
open_opportunity_ids (complete list). Optional: account_id (existing CRM ID,
null for new accounts), vertical (ICP id or null),
disqualifiers (known ICP ids). All public signals must have qualified bundles.

Factory owns territory, taxonomy, owner/house IDs and disqualifiers. Admission
requires one Tier 1 or two distinct Tier 2 types. Adoption additionally requires
an owned account and a web Tier 2 from this run. Open deals precede owner routing.
Routes: claim_new, claim_transfer, scan, active_deal, owned_elsewhere,
internal_domain. Only an admitted, in-territory claim route without hard
disqualifiers has claimable=true. Recoverable blockers and vertical rank are
reported. Exit 0 routing finding (not permission); 2 unusable input. JSON stdout.
"""
import argparse
from datetime import date, datetime, timedelta
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import factory

SHARED = Path(__file__).resolve().parents[1] / "_shared"
KEYS = {"domain", "headcount", "signals", "account_exists", "owner_id", "owner_is_active", "open_opportunity_ids"}
OPTIONAL = {"account_id", "vertical", "disqualifiers"}


def load_account_rules(shared):
    """Account/territory rules used by prospecting and ARR; no taxonomy read."""
    policy = json.loads((shared / "policy.json").read_text())
    factory.validate_policy(policy, ("identity", "routing"))
    icp_fm = factory.frontmatter(shared)
    low, high = icp_fm["territory"]["min_employees"], icp_fm["territory"]["max_employees"]
    factory.require(type(low) is int and type(high) is int and 0 <= low <= high, "invalid ICP employee range")
    return {
        "owner": policy["identity"]["owner_id"],
        "house": set(policy["routing"]["house_owner_ids"]),
        "min_emp": low,
        "max_emp": high,
        "vertical_rank": {v["id"]: int(v["rank"]) for v in icp_fm["verticals"]},
        "hard_dq": set(icp_fm["disqualifiers"]["hard"]),
        "recoverable_dq": set(icp_fm["disqualifiers"]["recoverable"]),
        "internal_domains": [factory.domain(d) for d in policy["identity"]["internal_domains"]],
    }


def load_rules(shared):
    policy = factory.read(shared / "policy.json")
    factory.validate_policy(policy, ("prospector",))
    return {**load_account_rules(shared),
            "signals": {s["id"]: s for entries in factory.taxonomy(shared)["tiers"].values() for s in entries}}


def admission(signals):
    unique = {s["signal_type"]: s for s in signals}
    tiers = [s.get("tier") for s in unique.values()]
    t1, t2 = tiers.count("tier1"), tiers.count("tier2")
    if t1 >= 1:
        return True, f"{t1} tier1"
    if t2 >= 2:
        return True, f"{t2} tier2"
    return False, f"{t1} tier1, {t2} tier2. Needs 1 tier1 or 2 tier2"


def territory(headcount, rules):
    if headcount is None:
        return "unknown"
    if type(headcount) is not int or headcount < 0:
        raise ValueError("headcount must be a nonnegative integer or null")
    return "in" if rules["min_emp"] <= headcount <= rules["max_emp"] else "out"


def route(r, rules):
    if r["open_opportunity_ids"]:
        return "active_deal"
    if not r["account_exists"]:
        return "claim_new"
    if r["owner_id"] == rules["owner"]:
        return "active_deal" if r["open_opportunity_ids"] else "scan"
    if r["owner_is_active"] is False or r["owner_id"] in rules["house"]:
        return "claim_transfer"
    return "owned_elsewhere"


def icp_fit(r, rules):
    vertical = r.get("vertical")
    if vertical is not None and not factory.nonblank(vertical):
        raise ValueError("vertical must be an ICP ID or null")
    if vertical is not None and vertical not in rules["vertical_rank"]:
        raise ValueError(f"unknown vertical {vertical!r}. Ids live in icp.md frontmatter")
    dqs = r.get("disqualifiers", [])
    if not isinstance(dqs, list) or any(not factory.nonblank(v) for v in dqs):
        raise ValueError("disqualifiers must be a list")
    unknown = sorted(set(dqs) - rules["hard_dq"] - rules["recoverable_dq"])
    if unknown:
        raise ValueError(f"unknown disqualifiers {unknown}. Ids live in icp.md frontmatter")
    hard = sorted(set(dqs) & rules["hard_dq"])
    recoverable = sorted(set(dqs) & rules["recoverable_dq"])
    rank = rules["vertical_rank"].get(vertical) if vertical else None
    return rank, hard, recoverable


def check(r, rules):
    if not isinstance(r, dict):
        raise ValueError("receipt must be an object")
    missing, extra = sorted(KEYS - set(r)), sorted(set(r) - KEYS - OPTIONAL)
    if missing or extra:
        raise ValueError(f"receipt keys mismatch: missing={missing} extra={extra}")
    if not isinstance(r["signals"], list) or not isinstance(r["open_opportunity_ids"], list):
        raise ValueError("signals and open_opportunity_ids must be lists")
    if type(r["account_exists"]) is not bool:
        raise ValueError("account_exists must be boolean")
    domain = factory.domain(r["domain"])
    if any(not factory.nonblank(v) for v in r["open_opportunity_ids"]):
        raise ValueError("open_opportunity_ids must contain nonblank string IDs")
    if r["account_exists"]:
        if not factory.nonblank(r["owner_id"]) or type(r["owner_is_active"]) is not bool:
            raise ValueError("existing Account needs a nonblank string owner_id and boolean owner_is_active")
    elif r["owner_id"] is not None or r["owner_is_active"] is not None or r["open_opportunity_ids"]:
        raise ValueError("new Account needs null owner fields and no open opportunities")
    if "account_id" in r and (not factory.nonblank(r["account_id"]) if r["account_exists"] else r["account_id"] is not None):
        raise ValueError("account_id must be an existing CRM ID, or null for a new Account")
    for s in r["signals"]:
        if not isinstance(s, dict):
            raise ValueError("each signal must be an object")
        if not factory.nonblank(s.get("signal_type")) or not isinstance(s.get("tier"), str):
            raise ValueError("signal_type and tier must be nonblank strings")
        configured = rules["signals"].get(s["signal_type"])
        if configured is None or s.get("tier") != f"tier{configured['tier']}":
            raise ValueError("signal id and tier must agree with the taxonomy")
    adoption = [s for s in r["signals"] if rules["signals"][s["signal_type"]].get("source") == "adoption"]
    web_t2 = [s for s in r["signals"] if s["tier"] == "tier2" and rules["signals"][s["signal_type"]].get("source", "web") == "web"]
    terr = territory(r["headcount"], rules)
    rank, hard, recoverable = icp_fit(r, rules)
    if any(domain == d or domain.endswith("." + d) for d in rules["internal_domains"]):
        return {"domain": domain, "route": "internal_domain", "claimable": False}
    admitted, why = admission(r["signals"])
    if adoption and (not web_t2 or not r["account_exists"] or r["owner_id"] != rules["owner"]):
        admitted, why = False, "adoption needs an owned Account and one web tier2 signal from this run"
    rt = route(r, rules)
    claimable = admitted and terr == "in" and not hard and rt in ("claim_new", "claim_transfer")
    return {"domain": domain, "admitted": admitted, "admission": why, "territory": terr,
            "vertical_rank": rank, "hard_disqualifiers": hard, "recoverable_blockers": recoverable,
            "route": rt, "claimable": claimable}


def scan_route(packet, policy, now):
    """Route a public scan using only policy and normalized CRM receipts.

    packet: {account: {id, name, domain, owner_id, owner_is_active,
      open_opportunity_ids: [str]} | null, tasks: [{id, owner_id, subject,
      created_at: aware ISO timestamp}], crm_complete: bool, tasks_complete: bool,
      activity_since: YYYY-MM-DD | null, read_reference: str | null}.
    Null account/coverage or false completeness records a limited finding.
    A complete read_reference identifies the completed CRM/activity reads;
    flags/references are assertions for review, not provider proof.
    """
    factory.validate_policy(policy, ("identity", "scan", "outreach"))
    factory.require(isinstance(now, datetime) and now.tzinfo is not None, "scan now must be timezone-aware")
    factory.require(isinstance(packet, dict), "scan CRM packet must be an object")
    required = {"account", "tasks", "crm_complete", "tasks_complete", "activity_since", "read_reference"}
    factory.require(required <= set(packet), "scan CRM packet is missing required fields")
    factory.require(all(type(packet[k]) is bool for k in ("crm_complete", "tasks_complete")), "scan completeness fields must be booleans")
    factory.require(isinstance(packet["tasks"], list), "scan tasks must be a list")
    factory.require(packet["read_reference"] is None or factory.nonblank(packet["read_reference"]), "scan read_reference must be nonblank or null")
    zone = ZoneInfo(policy["identity"]["timezone"])
    today = now.astimezone(zone).date()
    warm = policy["scan"]["warm_engagement"]
    lookback = max(policy["outreach"]["activity_lookback_days"], warm["lookback_days"])
    since = packet["activity_since"]
    if since is not None:
        factory.require(isinstance(since, str), "scan activity_since must be an ISO date or null")
        parsed = date.fromisoformat(since)
        factory.require(parsed.isoformat() == since and parsed <= today, "scan activity_since must be a canonical nonfuture date")
    else:
        parsed = None
    account = packet["account"]
    if account is not None:
        factory.require(isinstance(account, dict), "scan account must be an object or null")
        factory.require(all(factory.nonblank(account.get(k)) for k in ("id", "name", "owner_id")), "scan account IDs/name must be nonblank strings")
        factory.require(type(account.get("owner_is_active")) is bool, "scan owner_is_active must be boolean")
        factory.require(isinstance(account.get("open_opportunity_ids"), list) and all(factory.nonblank(v) for v in account["open_opportunity_ids"]), "scan open_opportunity_ids must be a list of IDs")
        domain = factory.domain(account.get("domain"))
    owner = policy["identity"]["owner_id"]
    ignored = set(warm["ignored_owner_ids"]) | {owner}
    others, engaged = set(), []
    for task in packet["tasks"]:
        factory.require(isinstance(task, dict) and all(factory.nonblank(task.get(k)) for k in ("id", "owner_id", "subject", "created_at")), "scan tasks need id, owner_id, subject and aware created_at")
        created = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
        factory.require(created.tzinfo is not None and created <= now, "scan task created_at must be aware and nonfuture")
        age = (today - created.astimezone(zone).date()).days
        if task["owner_id"] in ignored or age > lookback:
            continue
        others.add(task["owner_id"])
        if age <= warm["lookback_days"] and any(marker.casefold() in task["subject"].casefold() for marker in warm["task_subject_markers"]):
            engaged.append({k: task[k] for k in ("id", "owner_id", "subject", "created_at")})
    complete = (packet["crm_complete"] and packet["tasks_complete"] and account is not None
                and factory.nonblank(packet["read_reference"]) and parsed is not None
                and parsed <= today - timedelta(days=lookback))
    route_name = "unverified"
    if account is not None:
        if any(domain == factory.domain(d) or domain.endswith("." + factory.domain(d)) for d in policy["identity"]["internal_domains"]):
            route_name = "internal_domain"
        elif account["open_opportunity_ids"]:
            route_name = "active_deal"
        elif engaged:
            route_name = "warm_engaged"
        elif account["owner_id"] != owner:
            route_name = "owned_elsewhere"
        elif complete:
            route_name = "scan"
    return {"route": route_name, "handoff_eligible": complete and route_name == "scan",
            "required_lookback_days": lookback, "activity_complete": bool(complete),
            "other_owner_ids": sorted(others), "warm_tasks": engaged}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--shared", default=str(SHARED))
    a = ap.parse_args()
    try:
        r = json.loads(Path(a.receipt).read_text())
        out = check(r, load_rules(Path(a.shared)))
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(json.dumps({"verdict": "error", "reason": str(e)}))
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
