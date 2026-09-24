#!/usr/bin/env python3
"""Check a single proposed outreach email. No provider calls or writes.

Usage: python3 scripts/outreach_gate.py --packet packet.json [--shared DIR] [--now AWARE_TIMESTAMP]
Packet keys:
  bundle: qualified evidence_gate bundle, plus optional vertical.
  claim: {id, evidence, persona, pick_reason}; evidence is the selected row's exact
    evidence. pick_reason is one sentence tying the signal quote to that claim.
  recipient: {email, name, source, title, title_override}; override is a real
    user-supplied reason, or null. source equals a configured recipient source.
  activity: [{kind: task|event|mail_sent, date: ISO date, subtype, status, subject}].
  activity_complete: true only after all required CRM/mail pages were read.
  voice_anchor_reference: the approved or user-supplied email example reference.
  draft: {subject, body}.
Optional adoption_sentence requires adoption_bundle, adoption_review_reference
and adoption_checked_at. The sentence must exactly equal the approved category
statement, appear in body, and use the current completed data date.

Checks a nonblank pick_reason, current claim/signal/persona stamps,
held/status/claim boundaries, elapsed fetch age and signal freshness,
verified recipient/title, suppression, numbers,
proof names, copied evidence and cold-email lint. Matrix flags warn by default;
fit_mode=block holds them. Meaning, voice, truthful receipts and exact human
approval are reviewed in workflows/outreach/signal-outreach.md.
Exit 0 allow; 1 block with reasons and flags; 2 unusable input. JSON stdout.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import factory

sys.path.insert(0, str(Path(__file__).resolve().parent))
import approval  # noqa: E402
import lint_draft
import privacy_check

SHARED = Path(__file__).resolve().parents[1] / "_shared"
DATE_OPEN = re.compile(r"^\s*(on\s+)?(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2})", re.I)
NUM = re.compile(r"\d[\d,.]*\d|\d")
WORD = re.compile(r"[a-z0-9&'-]+")
EVIDENCE_RUN = 8


def norm(t):
    t = t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    return re.sub(r"\s+", " ", t).strip().lower()


def d(s):
    return date.fromisoformat(s[:10])


def parse_checked(s):
    """Timezone-aware datetime, or None when s is missing, date-only, or naive."""
    if not isinstance(s, str) or len(s) <= 10:
        return None
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo is not None else None


def numbers(t):
    return {n.rstrip(".,") for n in NUM.findall(t or "")}


INVITE = re.compile(
    r"\b(?:(?:worth|have|spare|for|grab|find)\s+(?:a\s+)?\d+\s+minutes?\b"
    r"|\d+\s+minute\s+(?:call|chat|conversation|meeting)\b)", re.I)


def question_sentence(body):
    parts = [x for x in re.split(r"(?<=[.?!])\s+", body.strip()) if x.strip()]
    hits = [x for x in parts if "?" in x]
    return hits[0] if len(hits) == 1 else ""


def strip_invite_minutes(body):
    """Remove meeting-invitation minute spans from the one question sentence only.

    Whitelisted shapes. 'worth 20 minutes', 'have 20 minutes', 'a 20 minute call'.
    Any other number in the question, including 'save 20 minutes per report', stays and is checked.
    Code cannot recognize an invitation by meaning. Drafting review owns that.
    """
    q = question_sentence(body)
    if not q:
        return body
    return body.replace(q, INVITE.sub(" ", q), 1)


def evidence_runs(evidence, body, n=EVIDENCE_RUN):
    e, b = WORD.findall(norm(evidence)), WORD.findall(norm(body))
    runs = {" ".join(e[i:i + n]) for i in range(len(e) - n + 1)}
    return [" ".join(b[i:i + n]) for i in range(len(b) - n + 1) if " ".join(b[i:i + n]) in runs]


def check(p, pol, shared, now):
    if now.tzinfo is None:
        raise ValueError("now must have a timezone")
    reasons = []
    today = now.astimezone(ZoneInfo(factory.read(shared / "policy.json")["identity"]["timezone"])).date()
    b, tt, rc, act, dr = p["bundle"], p["claim"], p["recipient"], p["activity"], p["draft"]
    if b.get("gate") != "evidence_gate" or not b.get("quote"):
        reasons.append("a qualified evidence bundle is required")
    if not isinstance(act, list) or p.get("activity_complete") is not True:
        reasons.append("complete CRM and sent-mail activity reads are required")
    if not isinstance(p.get("voice_anchor_reference"), str) or not p["voice_anchor_reference"].strip():
        reasons.append("an approved email voice anchor reference is required")
    if not isinstance(dr.get("body"), str) or not dr["body"].strip() or not isinstance(dr.get("subject"), str) or not dr["subject"].strip():
        raise ValueError("draft subject and body must be nonempty strings")
    tt_doc = factory.claim_document(shared)
    tracks = {t["id"]: t for t in tt_doc["claims"]}
    held = set((tt_doc).get("held") or [])
    tax = factory.taxonomy(shared)["tiers"]
    stype = next((t for tier in ("tier1", "tier2") for t in tax[tier] if t["id"] == b["signal_type"]), None)
    if stype is None:
        reasons.append(f"bundle signal_type not a tier1 or tier2 id: {b['signal_type']}")
    else:
        age = (today - d(b["published_date"])).days
        if age < 0:
            reasons.append("bundle published_date is in the future")
        if age > stype["freshness_days"]:
            reasons.append(f"bundle published_date {age} days old, {b['signal_type']} freshness is {stype['freshness_days']} days")
        if not approval.stamp_current(stype, stype.get(approval.STAMP_KEY)):
            reasons.append(f"signal type {b['signal_type']} changed since its approval stamp or has none")
    checked = parse_checked(b.get("checked_at") or b.get("checked_on"))
    if checked is None:
        reasons.append("bundle checked_at needs an ISO timestamp with a timezone offset. Re-read the source")
    elif checked > now:
        reasons.append("bundle checked_at is in the future")
    elif now - checked > timedelta(hours=pol["bundle_max_age_hours"]):
        reasons.append("bundle checked_at older than policy. Re-read the source")
    fm = factory.frontmatter(shared)
    cares = fm.get("persona_cares") or {}
    if not approval.stamp_current(cares, fm.get(approval.PERSONA_STAMP_KEY)):
        reasons.append("icp.md persona_cares changed since its approval stamp or has none")
    persona = tt.get("persona")
    if persona not in cares:
        reasons.append(f"claim.persona {persona!r} not an icp.md persona id")
    if not isinstance(tt.get("pick_reason"), str) or not tt["pick_reason"].strip():
        reasons.append("claim.pick_reason missing. One sentence tying the quote to the claim")
    row = tracks.get(tt["id"])
    body, subj = dr["body"], dr["subject"]
    if row is None:
        reasons.append(f"claim id not in claims.json: {tt['id']}")
    else:
        if row.get("status") != "approved":
            reasons.append("claim status is not approved")
        if row.get("kind") not in ("reported_example", "product_capability", "inference", "evaluation_advice") or not row.get("claim") or not row.get("limit"):
            reasons.append("claim needs kind, claim and limit")
        if tt["id"] in held:
            reasons.append(f"claim {tt['id']} is held in claims.json held")
        if norm(tt["evidence"]) != norm(row["evidence"]):
            reasons.append("claim evidence does not match the claims.json row")
        if not approval.stamp_current(row, row.get(approval.STAMP_KEY)):
            reasons.append(f"claim {tt['id']} changed since its approval stamp or has none")
        allowed = numbers(row.get("claim")) | numbers(row.get("track")) | numbers(b.get("quote"))
        stray = sorted(numbers(strip_invite_minutes(body)) - allowed)
        if stray:
            reasons.append(f"numbers in body not in the row's claim or track or the bundle quote: {', '.join(stray)}")
        runs = evidence_runs(row["evidence"], body)
        if runs:
            reasons.append(f"body copies {EVIDENCE_RUN} or more words from the row's evidence: {runs[0]!r}")
    subject_name = norm(b.get("evidence_subject") or "")
    prospect_name = norm(b.get("account_name") or "")
    nb = norm(body)
    for r in tt_doc["claims"]:
        name = norm(((r.get("proof") or {}).get("name")) or "")
        if not name or name in (subject_name, prospect_name) or name not in nb:
            continue
        ok = row is not None and r["id"] == row["id"] and bool(row["proof"].get("external_ok"))
        if not ok:
            reasons.append(f"body names {r['proof']['name']} from row {r['id']} proof. Only the chosen row's proof with external_ok true may be named")
    title = (rc.get("title") or "").strip()
    override = rc.get("title_override")
    if stype:
        tl = title.lower()
        hit = tl and any(tl in x.lower() or x.lower() in tl for x in stype["target_titles"])
        quoted = "the quoted executive" in [x.lower() for x in stype["target_titles"]]
        if quoted and norm(rc.get("name") or "") and norm(rc.get("name") or "") == subject_name:
            hit = True
        if not hit and not (isinstance(override, str) and override.strip()):
            reasons.append(f"recipient title {title or '(none)'!r} outside target_titles for {b['signal_type']}. Needs title_override from the reviewer")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", rc["email"]):
        reasons.append("recipient email is malformed")
    dom = rc["email"].rsplit("@", 1)[-1].lower()
    if dom != b["account_domain"].lower() and not dom.endswith("." + b["account_domain"].lower()):
        reasons.append("recipient domain does not match bundle account_domain")
    if rc["source"] not in pol["recipient_sources"]:
        reasons.append("recipient source not in policy. Needs the reviewer to name the address")
    cutoff = today - timedelta(days=pol["suppression_days"])
    for a in act:
        if a.get("kind") not in ("task", "event", "mail_sent"):
            raise ValueError("unrecognized activity kind; normalize the complete provider read")
        if a["kind"] == "task" and not a.get("status"):
            raise ValueError("task activity needs status")
        done = a["kind"] in ("mail_sent", "event") or (
            a.get("status") == "Completed" and a.get("subtype") in pol["suppressing_task_subtypes"])
        if done and d(a["date"]) >= cutoff:
            reasons.append(f"suppressed: {a['kind']} on {a['date'][:10]} inside suppression window")
            break
    if norm(b["quote"]) in nb:
        reasons.append("signal quote pasted whole into body")
    if len(subj.split()) > pol["subject_max_words"]:
        reasons.append("subject too long")
    if DATE_OPEN.match(body):
        reasons.append("body opens on a date")
    if body.count("?") != 1:
        reasons.append(f"body has {body.count('?')} question marks, needs exactly one")
    reasons.extend(lint_draft.check(body, pol["lint"]))
    if pol["fit_mode"] not in ("warn", "block"):
        raise ValueError("fit_mode must be warn or block")
    if pol["fit_mode"] == "block":
        reasons.extend(fit_flags(p, pol, shared))
    # This field makes an adoption assertion explicit; meaning still requires review.
    sentence = p.get("adoption_sentence")
    if sentence:
        full_policy = factory.read(shared / "policy.json")
        bundle = p.get("adoption_bundle")
        if not isinstance(bundle, dict):
            reasons.append("adoption sentence needs a reviewed bundle")
        else:
            reasons.extend(privacy_check.check(bundle, full_policy["adoption"]["bundle_keys"]))
            if bundle.get("account_domain", "").lower() != b["account_domain"].lower():
                reasons.append("adoption bundle is for a different account")
            permitted = full_policy["adoption"]["approved_statements"].get(bundle.get("adoption"))
            if full_policy["adoption"]["enabled"] is not True:
                reasons.append("adoption adapter disabled")
            if bundle.get("data_through_date") != (today - timedelta(days=full_policy["adoption"]["data_lag_days"])).isoformat():
                reasons.append("adoption bundle is not for the configured complete data date")
            if not permitted or sentence != permitted or sentence not in body or not p.get("adoption_review_reference"):
                reasons.append("adoption sentence must equal the reviewed category statement")
            if not p.get("adoption_checked_at") or parse_checked(p["adoption_checked_at"]) is None:
                reasons.append("adoption source needs a fresh checked_at")
            else:
                checked_adoption = parse_checked(p["adoption_checked_at"])
                if checked_adoption > now or now - checked_adoption > timedelta(hours=pol["bundle_max_age_hours"]):
                    reasons.append("adoption source is stale or in the future")
    return reasons


def fit_flags(p, pol, shared):
    """Describe matrix gaps; the caller applies the configured fit mode."""
    flags = []
    b, tt = p["bundle"], p["claim"]
    tt_doc = json.loads((shared / "claims.json").read_text())
    row = next((t for t in tt_doc["claims"] if t["id"] == tt["id"]), None)
    if row is None:
        return flags
    tax = factory.taxonomy(shared)["tiers"]
    stype = next((t for tier in ("tier1", "tier2") for t in tax[tier] if t["id"] == b["signal_type"]), None)
    rv = row.get("verticals") or []
    vertical_fit = "all" in rv or b.get("vertical") in rv
    bound = stype is not None and tt["id"] in stype["claim_ids"]
    if not bound:
        flags.append(f"best guess. claim {tt['id']} is outside the {b['signal_type']} binding")
    if not vertical_fit:
        flags.append(f"best guess. claim {tt['id']} verticals {rv} do not include bundle vertical {b.get('vertical')!r}")
    persona = tt.get("persona")
    if persona not in (row.get("personas") or []):
        flags.append(f"best guess. claim {tt['id']} personas do not include {persona}")
    return flags


def parse_now(s):
    if not s:
        return datetime.now().astimezone()
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("now requires a timestamp with timezone offset")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", required=True)
    ap.add_argument("--shared", default=str(SHARED))
    ap.add_argument("--now", "--today", dest="now", default=None, help="ISO timestamp with offset. Defaults to the current local time; date-only values are rejected")
    a = ap.parse_args()
    try:
        shared = Path(a.shared)
        pol = json.loads((shared / "policy.json").read_text())["outreach"]
        p = json.loads(Path(a.packet).read_text())
        reasons = check(p, pol, shared, parse_now(a.now))
        flags = fit_flags(p, pol, shared)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(json.dumps({"verdict": "error", "reason": f"{type(e).__name__}: {e}"}))
        return 2
    if reasons:
        print(json.dumps({"verdict": "block", "reasons": reasons, "flags": flags}, indent=2))
        return 1
    print(json.dumps({"verdict": "allow", "recipient": p["recipient"]["email"], "signal_type": p["bundle"]["signal_type"],
                      "claim_id": p["claim"]["id"], "flags": flags}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
