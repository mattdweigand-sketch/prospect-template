#!/usr/bin/env python3
"""Emit the verdict and Next line for one signal-scan run. signal-scan copies both verbatim.

Usage:
    python3 scripts/scan_verdict.py <gate_output.json> [<gate_output.json> ...]

Arguments are evidence_gate.py outputs in report order. Position is the report's signal number
(the first file is Signal 1). Each file is {"outcome": "qualified", "bundle": {...}} or a
no_usable_signal / unusable output. Files that did not qualify are counted and otherwise ignored.

Rule, in code so no run can add a bar. Any qualified signal on an owned account is a reason to
reach out. Recommended signal is the newest tier1, else the newest tier2, ties to the lower number.
Taxonomy admission (1 tier1 or 2 tier2) belongs to signal-prospector and route_candidate.py only.

A fit rejection is not made here. The report names it per item as "Rejected on fit, <reason>" and
the verdict line stays as emitted.

Exit 0 verdict JSON on stdout. Exit 2 unusable input. Never a traceback.
"""
import json
import sys

TIER_ORDER = {"tier1": 0, "tier2": 1}


def load(paths):
    outs = []
    for p in paths:
        try:
            with open(p) as fh:
                outs.append(json.load(fh))
        except (OSError, json.JSONDecodeError) as e:
            return None, {"outcome": "unusable", "reason": "unreadable_gate_output", "path": p, "detail": str(e)}
    return outs, None


def verdict(outs):
    qualified = []
    for n, o in enumerate(outs, start=1):
        if not isinstance(o, dict) or o.get("outcome") != "qualified":
            continue
        b = o.get("bundle") or {}
        if not isinstance(b, dict):
            return {"outcome": "unusable", "reason": "qualified_bundle_not_object", "signal": n}
        tier = b.get("tier")
        if tier not in TIER_ORDER:
            return {"outcome": "unusable", "reason": "qualified_bundle_without_tier", "signal": n}
        if b.get("published_date") is not None and not isinstance(b["published_date"], str):
            return {"outcome": "unusable", "reason": "invalid_qualified_date", "signal": n}
        qualified.append({"signal": n, "signal_type": b.get("signal_type"), "tier": tier,
                          "published_date": b.get("published_date")})
    checked = len(outs)
    if not qualified:
        return {"checked": checked, "qualified": [], "recommended": None,
                "verdict": "Nothing qualified. Not proof of absence.",
                "next": "Stop"}
    rec = sorted(qualified, key=lambda q: (TIER_ORDER[q["tier"]], _date_key(q["published_date"]), q["signal"]))[0]
    return {"checked": checked, "qualified": qualified, "recommended": rec["signal"],
            "verdict": f"Signal {rec['signal']} qualified.",
            "next": f"signal-outreach with Signal {rec['signal']}"}


def _date_key(d):
    # ISO dates sort lexically. Newest first means descending, so invert each character.
    if not d:
        return "\uffff"  # above every inverted digit, so a missing date sorts after every real date
    return "".join(chr(0xFFFF - ord(c)) for c in d)


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
