#!/usr/bin/env python3
"""Read-only checks of a proposed or installed messaging configuration.

--source is the explicit local clone/snapshot of policy.refresh.source; no fetch
is performed. Evidence is checked at claims.source_revision, never HEAD by default.
Exit 0: messaging checks pass; 1: incomplete configuration; 2: unusable input.
Passing checks do not prove meaning, human approval or provider readiness.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

import approval
import build_pairings
import factory
import refresh_tracks


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, empty=False):
    return isinstance(value, list) and (empty or bool(value)) and all(nonblank(v) for v in value) and len(value) == len(set(value))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def structure(policy, doc, tax, icp):
    require(policy.get("schema_version") == 2 and policy.get("mode") in ("example", "live"), "policy must use schema 2 and example/live mode")
    identity = policy["identity"]
    require(all(nonblank(identity.get(k)) for k in ("owner_id", "owner_email", "timezone")), "configure owner ID, email and timezone")
    require(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", identity["owner_email"]), "owner email is malformed")
    ZoneInfo(identity["timezone"])
    require(strings(identity.get("internal_domains")), "configure internal domains")
    outreach = policy["outreach"]
    factory.task_status_map(outreach)
    for field in ("suppression_days", "activity_lookback_days", "bundle_max_age_hours", "subject_max_words", "max_drafts"):
        require(type(outreach.get(field)) is int and outreach[field] >= (0 if field == "suppression_days" else 1), "invalid outreach." + field)
    require(outreach["activity_lookback_days"] >= outreach["suppression_days"], "activity lookback must cover suppression")
    require(outreach.get("fit_mode") in ("warn", "block"), "fit_mode must be warn or block")
    require(strings(outreach.get("recipient_sources")), "configure recipient sources")
    require(type(outreach["lint"].get("max_body_words")) is int and outreach["lint"]["max_body_words"] > 0, "configure a positive body word limit")
    require(all(nonblank(policy["email_voice"].get(k)) for k in ("greeting", "closing", "body")), "configure email voice")
    for capability in ("adoption", "arr_growth"):
        require(type(policy[capability].get("enabled")) is bool, "capabilities must be explicitly enabled or disabled")
    required_inputs = {"_shared/adapters.md", "_shared/icp.md", "_shared/taxonomy.json", "_shared/claims.json"}
    require(strings(policy.get("review_inputs")) and required_inputs <= set(policy["review_inputs"]), "review_inputs must cover all messaging configuration")
    territory = icp["territory"]
    low, high = territory["min_employees"], territory["max_employees"]
    require(type(low) is int and type(high) is int and 0 <= low <= high, "invalid ICP employee range")
    verticals = icp["verticals"]
    require(isinstance(verticals, list) and bool(verticals), "configure ICP verticals")
    require(strings([v["id"] for v in verticals]) and all(type(v["rank"]) is int and v["rank"] > 0 for v in verticals), "vertical IDs must be unique with positive integer ranks")
    require(all(strings(icp["disqualifiers"].get(k), empty=True) for k in ("hard", "recoverable")), "configure explicit hard/recoverable disqualifier lists")
    cares = icp["persona_cares"]
    require(isinstance(cares, dict) and bool(cares) and all(nonblank(k) and nonblank(v) for k, v in cares.items()), "configure buyer responsibilities in persona_cares")
    rows, signals = doc["claims"], tax["signals"]
    require(isinstance(rows, list) and bool(rows) and strings([r["id"] for r in rows]), "configure unique nonempty claim IDs")
    require(isinstance(signals, list) and bool(signals) and strings([s["id"] for s in signals]), "configure unique nonempty signal IDs")
    ids, vertical_ids = {r["id"] for r in rows}, {v["id"] for v in verticals} | {"all"}
    require(strings(doc.get("held"), empty=True) and set(doc["held"]) <= ids, "held must list known claim IDs")
    for row in rows:
        rid = row["id"]
        require(all(nonblank(row.get(k)) for k in ("claim", "limit", "track", "evidence", "source_reference", "status")), "missing claim content: " + rid)
        require(row.get("kind") in ("reported_example", "product_capability", "inference", "evaluation_advice"), "invalid claim kind: " + rid)
        require(strings(row.get("verticals")) and set(row["verticals"]) <= vertical_ids, "unknown/empty claim verticals: " + rid)
        require(strings(row.get("personas")) and set(row["personas"]) <= set(cares), "unknown/empty claim personas: " + rid)
        proof = row["proof"]
        require(isinstance(proof, dict) and type(proof.get("external_ok")) is bool, "invalid proof permission: " + rid)
        require(not proof["external_ok"] or nonblank(proof.get("name")), "external proof permission requires a named proof: " + rid)
        refresh_tracks.source_path(doc["source_root"], row["source_reference"])
    for signal in signals:
        sid = signal["id"]
        require(type(signal.get("tier")) is int and signal["tier"] in (1, 2, 3), "invalid signal tier: " + sid)
        require(signal.get("source") in ("web", "adoption"), "invalid signal source: " + sid)
        require(type(signal.get("freshness_days")) is int and signal["freshness_days"] >= 0, "invalid signal freshness: " + sid)
        require(all(nonblank(signal.get(k)) for k in ("definition", "creates_work")), "signal needs definition and resulting work: " + sid)
        require(strings(signal.get("target_titles")) and strings(signal.get("example_queries"), empty=signal["source"] != "web" or signal["tier"] == 3), "configure signal titles and example_queries: " + sid)
        require(strings(signal.get("claim_ids"), empty=True) and set(signal["claim_ids"]) <= ids, "unknown or malformed claim bindings: " + sid)
    if policy["adoption"]["enabled"]:
        require(any(s["id"] == policy["prospector"]["adoption_signal_id"] and s["source"] == "adoption" for s in signals), "enabled adoption needs its configured taxonomy signal")


def validate(shared=factory.SHARED, source=None):
    shared = Path(shared)
    issues, evidence = [], None
    report = {"messaging": {"state": "incomplete", "issues": issues},
              "connectors": {"state": "not_verified", "configuration": str(shared / "adapters.md"),
                             "reason": "Provider mappings and live read receipts require separate review; this check makes no provider calls."},
              "note": "Proposed stamps are not approval. Review meaning, source attribution, samples and exact file changes before installation."}
    try:
        policy = factory.read(shared / "policy.json")
        doc, tax, icp = factory.claim_document(shared), factory.taxonomy(shared), factory.frontmatter(shared)
        structure(policy, doc, tax, icp)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        issues.append("Configuration: " + str(exc))
        return report
    if icp.get("status") == "example":
        issues.append("ICP still has example status; review and configure it")
    if not nonblank(policy["email_voice"].get("anchor_reference")):
        issues.append("Supply an approved email voice anchor reference")
    if not approval.stamp_current(icp["persona_cares"], icp.get("persona_cares_approved")):
        issues.append("Persona responsibilities have no current stamp")
    active = [r for r in doc["claims"] if r["id"] not in doc["held"]]
    usable = {r["id"] for r in active if r["status"] == "approved" and nonblank(r.get("approval_reference")) and approval.stamp_current(r, r.get("approved"))}
    for row in active:
        if row["id"] not in usable:
            issues.append("Claim needs reviewed status, reference and current stamp: " + row["id"])
    public = [s for s in tax["signals"] if s["tier"] in (1, 2) and s["source"] == "web"]
    if not public:
        issues.append("Configure at least one public Tier 1/2 signal")
    for signal in tax["signals"]:
        if signal["tier"] in (1, 2) and (signal["source"] == "web" or policy["adoption"]["enabled"]):
            if not approval.stamp_current(signal, signal.get("approved")):
                issues.append("Signal has no current stamp: " + signal["id"])
            if signal["source"] == "web" and not usable.intersection(signal["claim_ids"]):
                issues.append("Public signal has no usable bound claim: " + signal["id"])
    _, bindings = build_pairings.build(shared)
    issues.extend(bindings)
    if not nonblank(policy["refresh"].get("source")):
        issues.append("Configure the retained knowledge source in policy.refresh.source")
    revision = doc.get("source_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        issues.append("Claims need a pinned full Git source revision")
    elif source is None:
        issues.append("Pass --source with the local clone/snapshot to verify evidence")
    else:
        try:
            evidence = refresh_tracks.report(Path(source), shared, revision)
            for key in ("broken_rows", "missing_pages", "missing_watch_pages", "contradiction_flags"):
                if evidence[key]:
                    issues.append("Source check: " + key)
            if evidence["head"] != revision or doc.get("source_date") != evidence["head_date"]:
                issues.append("Source revision/date do not match the pinned commit")
            date.fromisoformat(doc["evidence_verified"])
        except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
            issues.append("Source check: " + str(exc))
    report["messaging"].update(state="incomplete" if issues else "checks_passed", usable_claims=len(usable), public_signals=len(public))
    report["source_report"] = evidence
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared", type=Path, default=factory.SHARED)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args.shared, args.source)
        print(json.dumps(report, indent=2))
        return int(report["messaging"]["state"] != "checks_passed")
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"verdict": "error", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
