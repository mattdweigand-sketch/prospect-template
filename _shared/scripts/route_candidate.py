#!/usr/bin/env python3
"""Admit and route one net-new candidate account. signal-prospector calls this once per candidate.

Usage:
    python3 _shared/scripts/route_candidate.py --receipt receipt.json [--shared _shared]

receipt.json
    {
      "domain": "acme.example",
      "headcount": 1200 | null,                 # verified employee count of the buying entity, null when unknown
      "signals": [{"signal_type": "...", "tier": "tier1"}],   # web bundles that passed evidence_gate.py, plus at most
                                                              # one warehouse signal built by signal-prospector from
                                                              # adoption_territory.sql
      "account_exists": true | false,
      "owner_id": "owner-123" | null,
      "owner_is_active": true | false | null,
      "open_deal_ids": ["deal-123"],
      "vertical": "professional_services" | null,     # optional. An id from icp.md frontmatter verticals, null when unknown
      "disqualifiers": ["outside_offer_scope"]   # optional. Ids from icp.md frontmatter disqualifiers seen in evidence
    }

Rules come from .local/config/signals.md (tier ids, admission thresholds, warehouse pairing), .local/config/icp.md
frontmatter (territory, verticals, disqualifiers), and .local/config/policy.yaml (identity.crm_user_id,
crm.house_owner_ids). Never edit them here.

Admission. Every signal names a tier1, tier2, or tier3 id and the tier the taxonomy gives it. Anything else is exit 2.
tier3 never counts. Warehouse signals (taxonomy entries with `source`) count at most admission.warehouse_max_counted
times, default 1 when the key is absent, and only when a web tier2 signal is beside them
(admission.warehouse_needs_web_tier2). Then admission.tier1_min tier1 or admission.tier2_min tier2.

Routes: claim_new, claim_transfer, scan, active_deal, owned_elsewhere. route() is the route table.
Order. No Account, claim_new. Any open deal, active_deal. Inactive owner or an id in house_owner_ids,
claim_transfer. Owner is identity.crm_user_id, scan. Any other owner, owned_elsewhere.
A claim route is only emitted when admitted, in territory, and free of hard disqualifiers. Otherwise the route is kept and
`claimable` is false. `vertical_rank` is the icp.md rank or null. An unknown vertical or disqualifier id is exit 2.

Exit 0 verdict JSON on stdout. Exit 2 unusable input, {"verdict": "error", "reason": ...}. Never a traceback.
"""
import argparse
import json
import sys
from pathlib import Path

import common

KEYS = {"domain", "headcount", "signals", "account_exists", "owner_id", "owner_is_active", "open_deal_ids"}
OPTIONAL = {"vertical", "disqualifiers"}
COUNTED_TIERS = ("tier1", "tier2")


def load_rules(shared):
    policy = common.load_policy(shared)
    icp_fm = common.icp_frontmatter(shared)
    tax = common.load_taxonomy(shared)
    return {
        "owner": policy["identity"]["crm_user_id"],
        "house": set(policy["crm"]["house_owner_ids"]),
        "min_emp": int(icp_fm["territory"]["min_employees"]),
        "max_emp": int(icp_fm["territory"]["max_employees"]),
        "vertical_rank": {v["id"]: int(v["rank"]) for v in icp_fm["verticals"]},
        "hard_dq": set(icp_fm["disqualifiers"]["hard"]),
        "recoverable_dq": set(icp_fm["disqualifiers"]["recoverable"]),
        "types": common.taxonomy_types(tax),
        "admission": {"tier1_min": int(tax["admission"]["tier1_min"]), "tier2_min": int(tax["admission"]["tier2_min"]),
                      "warehouse_needs_web_tier2": bool(tax["admission"]["warehouse_needs_web_tier2"]),
                      "warehouse_max_counted": int(tax["admission"].get("warehouse_max_counted", 1))},
    }


def admission(signals, rules):
    web = {"tier1": 0, "tier2": 0}
    warehouse = []
    for s in signals:
        if not isinstance(s, dict) or "signal_type" not in s or "tier" not in s:
            raise ValueError("each signal must be an object with signal_type and tier")
        t = rules["types"].get(s["signal_type"])
        if t is None or t["tier"] != s["tier"]:
            raise ValueError(f"unknown or mis-tiered signal {s['signal_type']!r} as {s['tier']!r}. Ids and tiers live in signals.md")
        if s["tier"] not in COUNTED_TIERS:
            continue
        if t["source"]:
            warehouse.append(s["tier"])
        else:
            web[s["tier"]] += 1
    adm = rules["admission"]
    notes = []
    counted = dict(web)
    if warehouse:
        if adm["warehouse_needs_web_tier2"] and web["tier2"] < 1:
            notes.append("warehouse signals not counted, need one web tier2 beside them")
        else:
            for tier in warehouse[:adm["warehouse_max_counted"]]:
                counted[tier] += 1
        extra = len(warehouse) - adm["warehouse_max_counted"]
        if extra > 0:
            notes.append(f"{extra} extra warehouse signal ignored, at most {adm['warehouse_max_counted']} count")
    t1, t2 = counted["tier1"], counted["tier2"]
    why = f"{t1} tier1, {t2} tier2" + (". " + ". ".join(notes) if notes else "")
    if t1 >= adm["tier1_min"] or t2 >= adm["tier2_min"]:
        return True, why
    return False, f"{why}. Needs {adm['tier1_min']} tier1 or {adm['tier2_min']} tier2"


def territory(headcount, rules):
    if headcount is None:
        return "unknown"
    return "in" if rules["min_emp"] <= int(headcount) <= rules["max_emp"] else "out"


def route(r, rules):
    if not isinstance(r["account_exists"], bool):
        raise ValueError("account_exists must be a boolean, not an unknown read")
    if not isinstance(r["open_deal_ids"], list) or any(
            not isinstance(v, str) or not v.strip() for v in r["open_deal_ids"]):
        raise ValueError("open_deal_ids must be a list of nonempty ids")
    if r["account_exists"] and (not isinstance(r["owner_id"], str) or not r["owner_id"].strip()
                                or not isinstance(r["owner_is_active"], bool)):
        raise ValueError("existing Account needs owner_id and boolean owner_is_active")
    if not r["account_exists"]:
        if r["open_deal_ids"]:
            raise ValueError("absent Account cannot have open deals")
        return "claim_new"
    if r["open_deal_ids"]:
        return "active_deal"
    if r["owner_is_active"] is False or r["owner_id"] in rules["house"]:
        return "claim_transfer"
    if r["owner_id"] == rules["owner"]:
        return "scan"
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
    missing, extra = sorted(KEYS - set(r)), sorted(set(r) - KEYS - OPTIONAL)
    if missing or extra:
        raise ValueError(f"receipt keys mismatch: missing={missing} extra={extra}")
    if not isinstance(r["signals"], list) or not isinstance(r["open_deal_ids"], list):
        raise ValueError("signals and open_deal_ids must be lists")
    admitted, why = admission(r["signals"], rules)
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
    ap.add_argument("--shared", default=str(common.SHARED))
    a = ap.parse_args()
    try:
        r = json.loads(Path(a.receipt).read_text())
        if not isinstance(r, dict):
            raise ValueError("receipt must be a JSON object")
        out = check(r, load_rules(Path(a.shared)))
    except common.INPUT_ERRORS as e:
        print(common.error_json(e))
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
