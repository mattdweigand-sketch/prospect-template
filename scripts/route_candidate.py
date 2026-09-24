#!/usr/bin/env python3
"""Admit and route one prospecting candidate. No provider calls or writes.

Usage: python3 scripts/route_candidate.py --receipt FILE [--shared DIR]
Receipt required keys: domain (normalized host), headcount (verified nonnegative
integer or null), signals [{signal_type, tier: tier1|tier2|tier3}], account_exists
(boolean), owner_id (string or null), owner_is_active (boolean or null),
open_opportunity_ids (complete list). Optional: vertical (ICP id or null),
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
import json
import sys
from pathlib import Path

import factory

SHARED = Path(__file__).resolve().parents[1] / "_shared"
KEYS = {"domain", "headcount", "signals", "account_exists", "owner_id", "owner_is_active", "open_opportunity_ids"}
OPTIONAL = {"vertical", "disqualifiers"}


def load_rules(shared):
    policy = json.loads((shared / "policy.json").read_text())
    icp_fm = factory.frontmatter(shared)
    return {
        "owner": policy["identity"]["owner_id"],
        "house": set(policy["routing"]["house_owner_ids"]),
        "min_emp": int(icp_fm["territory"]["min_employees"]),
        "max_emp": int(icp_fm["territory"]["max_employees"]),
        "vertical_rank": {v["id"]: int(v["rank"]) for v in icp_fm["verticals"]},
        "hard_dq": set(icp_fm["disqualifiers"]["hard"]),
        "recoverable_dq": set(icp_fm["disqualifiers"]["recoverable"]),
        "signals": {s["id"]: s for entries in factory.taxonomy(shared)["tiers"].values() for s in entries},
        "internal_domains": [d.lower() for d in policy["identity"]["internal_domains"]],
    }


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
    if vertical is not None and vertical not in rules["vertical_rank"]:
        raise ValueError(f"unknown vertical {vertical!r}. Ids live in icp.md frontmatter")
    dqs = r.get("disqualifiers") or []
    if not isinstance(dqs, list):
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
    if not isinstance(r["domain"], str):
        raise ValueError("domain must be a normalized host")
    domain = r["domain"].lower()
    if not domain or any(c in domain for c in "@ /:"):
        raise ValueError("domain must be a normalized host")
    if any(domain == d or domain.endswith("." + d) for d in rules["internal_domains"]):
        return {"domain": domain, "route": "internal_domain", "claimable": False}
    for s in r["signals"]:
        if not isinstance(s, dict):
            raise ValueError("each signal must be an object")
        configured = rules["signals"].get(s.get("signal_type"))
        if configured is None or s.get("tier") != f"tier{configured['tier']}":
            raise ValueError("signal id and tier must agree with the taxonomy")
    adoption = [s for s in r["signals"] if rules["signals"][s["signal_type"]].get("source") == "adoption"]
    web_t2 = [s for s in r["signals"] if s["tier"] == "tier2" and rules["signals"][s["signal_type"]].get("source", "web") == "web"]
    if r["account_exists"] and (not r["owner_id"] or not isinstance(r["owner_is_active"], bool)):
        raise ValueError("existing Account needs owner_id and boolean owner_is_active")
    admitted, why = admission(r["signals"])
    if adoption and (not web_t2 or not r["account_exists"] or r["owner_id"] != rules["owner"]):
        admitted, why = False, "adoption needs an owned Account and one web tier2 signal from this run"
    terr = territory(r["headcount"], rules)
    rt = route(r, rules)
    rank, hard, recoverable = icp_fit(r, rules)
    claimable = admitted and terr == "in" and not hard and rt in ("claim_new", "claim_transfer")
    return {"domain": r["domain"], "admitted": admitted, "admission": why, "territory": terr,
            "vertical_rank": rank, "hard_disqualifiers": hard, "recoverable_blockers": recoverable,
            "route": rt, "claimable": claimable}


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
