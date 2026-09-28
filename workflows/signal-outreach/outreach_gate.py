#!/usr/bin/env python3
"""Check one outreach packet before a Gmail draft proposal. Never sends or proves approval.

Caller: signal-outreach. Usage: python3 workflows/signal-outreach/outreach_gate.py --packet p.json
[--shared _shared] [--now ISO-with-offset]. --now is for tests only.

Packet:
  bundle: the current evidence_gate bundle (classification active_initiative, relevance employee_use),
    or a paid_individuals_present wrapper with published_date, checked_at, quote, account_name,
    account_domain, date_basis warehouse, and the complete privacy-checked adoption_bundle.
  talk_track: {angle: plain-language angle from talk-track.md, persona: verified responsibility,
               pick_reason: one sentence connecting the source, person, and message}
  recipient: {email, name, source, title, contact_id: Salesforce Contact Id or null}
  activity: unfiltered live-read rows {kind: task|event|gmail_sent, date: YYYY-MM-DD,
             who: Contact/Lead Id|email|null, status and subtype for tasks}.
  reads: {tasks, events, gmail_sent}, each {complete: true, query_reference: native call reference,
          checked_at: aware timestamp, account_domain: bundle domain, recipient_email: recipient,
          window_start: YYYY-MM-DD}. An empty activity list never stands in for these receipts.
  account: {id, domain, owner_id, owner_is_active: true, open_opportunity_ids: []},
          current native Account and Opportunity reads; procedure retains their call references.
  draft: {subject, body}

Checks: qualifying signal id; active employee-use public evidence; warehouse privacy and exact allowed
statement; published-date freshness; aware checked_at within policy; nonempty messaging judgment;
talk-track review date; recipient identity/domain/source; contact-specific suppression; numbers grounded
in the quote. Meeting-invitation minute spans in the single question are exempt. Unrecognized titles do
not require a mapping or override. Claim support, role fit and wording remain the agent's explicit review
and the seller's exact proposal approval. There are no numbered answers or evidence-ID mappings.

Flags: capability wording marked verify_before_action is advisory. No flag authorizes a write.
Exit 0 allow, 1 block, 2 unusable input; always JSON. Required reads and exact approval/readback are
performed by the procedure; a fabricated packet is not proof of provider reads or human approval.
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared" / "scripts"))
import common  # noqa: E402
import privacy_check  # noqa: E402

SHARED = common.SHARED
NUM = re.compile(r"\d[\d,.]*\d|\d")
VERIFY = re.compile(r"\b(available|included|supports|guarantees)\b", re.I)


def load_talk_track(shared):
    """talk-track.md as a dict, through common."""
    return common.load_talk_track(shared)


def norm(t):
    t = t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    return re.sub(r"\s+", " ", t).strip().lower()


def d(s):
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise ValueError("date must be YYYY-MM-DD")
    return date.fromisoformat(s)


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def domain(value):
    """A plain DNS domain, not a URL, email address, or empty suffix."""
    if not nonblank(value):
        return None
    value = value.strip().lower()
    label = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    return value if re.fullmatch(label + r"(?:\." + label + r")+", value) else None


def email_domain(value):
    if nonblank(value) and re.fullmatch(r"[^\s@<>,;]+@[^\s@<>,;]+", value.strip()):
        return domain(value.strip().rsplit("@", 1)[1])
    return None


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


def warehouse_reasons(b, shared):
    """Check 1 for a signal type whose taxonomy entry names a non-web source."""
    us = common.load_policy(shared)["user_scan"]
    ab = b.get("adoption_bundle")
    if not isinstance(ab, dict):
        return [f"{b['signal_type']} needs adoption_bundle, the privacy-checked signal-user-scan bundle"]
    reasons = [f"adoption_bundle failed privacy_check: {x}"
               for x in privacy_check.check(ab, us["bundle_keys"], list(us["adoption_values"]))]
    if ab.get("adoption") != "individuals_only":
        reasons.append(f"adoption_bundle adoption is {ab.get('adoption')!r}, {b['signal_type']} needs individuals_only")
    if norm(b.get("quote") or "") != norm(us["statements"]["individuals_only"]):
        reasons.append("bundle quote must equal user_scan.statements.individuals_only")
    for key in ("account_name", "account_domain", "salesforce_account_id", "data_through_date"):
        if not nonblank(ab.get(key)):
            reasons.append(f"adoption_bundle {key} must be a nonempty string")
    for wrapper_key, embedded_key in (("account_name", "account_name"), ("account_domain", "account_domain"),
                                      ("published_date", "data_through_date")):
        left, right = b.get(wrapper_key), ab.get(embedded_key)
        matches = nonblank(left) and nonblank(right) and (
            left == right if wrapper_key == "published_date" else norm(left) == norm(right))
        if not matches:
            reasons.append(f"bundle {wrapper_key} must match adoption_bundle {embedded_key}")
    return reasons


def check(p, pol, shared, now):
    reasons = []
    now = now.astimezone(common.policy_tz(common.load_policy(shared)))
    today = now.date()
    b, tt, rc, act, dr = p["bundle"], p["talk_track"], p["recipient"], p["activity"], p["draft"]
    for label, obj in (("bundle", b), ("talk_track", tt), ("recipient", rc), ("draft", dr)):
        if not isinstance(obj, dict):
            raise ValueError(f"{label} must be an object")
    if not isinstance(act, list):
        raise ValueError("activity must be the unfiltered live-read list, empty when no rows exist")
    for key in ("account_name", "quote"):
        if not nonblank(b.get(key)):
            reasons.append(f"bundle {key} must be a nonempty string")
    account_domain = domain(b.get("account_domain"))
    if account_domain is None:
        reasons.append("bundle account_domain must be a usable domain")
    for key in ("subject", "body"):
        if not nonblank(dr.get(key)):
            raise ValueError(f"draft {key} must be a nonempty string")
    tt_doc = load_talk_track(shared)
    meta = tt_doc.get("meta") or {}
    stype, _tier = common.taxonomy_entry(common.load_taxonomy(shared), b["signal_type"])
    warehouse = bool(stype and stype.get("source"))
    if stype is None:
        reasons.append(f"bundle signal_type not a tier1 or tier2 id: {b['signal_type']}")
    else:
        if not warehouse:
            if b.get("gate") != "evidence_gate":
                reasons.append("web bundle requires the evidence_gate result")
            parsed = urlsplit(b.get("source_url") or "")
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                reasons.append("web bundle requires a usable source_url")
            if b.get("date_basis") not in ("published", "page_event", "linkedin_post_id"):
                reasons.append("web bundle requires a verified date_basis")
            if b.get("classification") != "active_initiative":
                reasons.append("web bundle needs active_initiative classification; rescan old bundles")
            if b.get("relevance") != "employee_use":
                reasons.append("web bundle must establish employee_use; API and unclear findings do not enter this workflow")
        if warehouse:
            if b.get("gate") == "evidence_gate" or b.get("source_url"):
                reasons.append(f"{b['signal_type']} is sourced from {stype['source']}, not the web. "
                               "A page never qualifies it. Use the signal-user-scan bundle")
            reasons.extend(warehouse_reasons(b, shared))
        published = d(b["published_date"])
        if published > max(today, now.astimezone(timezone.utc).date()):
            reasons.append("bundle published_date is in the future")
        age = (today - published).days
        if age > stype["freshness_days"]:
            reasons.append(f"bundle published_date {age} days old, {b['signal_type']} freshness is {stype['freshness_days']} days")
    checked = common.parse_iso(b.get("checked_at") or b.get("checked_on"))
    if checked is None:
        reasons.append("bundle checked_at needs an ISO timestamp with a timezone offset. Re-read the source")
    elif checked > now:
        reasons.append("bundle checked_at is in the future. Re-read the source")
    elif now - checked > timedelta(hours=pol["bundle_checked_max_age_hours"]):
        reasons.append("bundle checked_at older than policy. Re-read the source")
    # Judgment must be stated for human review; code does not determine its truth.
    for key in ("angle", "persona", "pick_reason"):
        if not nonblank(tt.get(key)):
            reasons.append(f"talk_track.{key} must be a nonempty explanation")
    body, subj = dr["body"], dr["subject"]
    review_by = str(meta.get("review_by") or "")
    if not review_by:
        reasons.append("talk-track.md meta.review_by missing. Review the track and set the date")
    elif d(review_by) < today:
        reasons.append(f"talk-track.md meta.review_by {review_by[:10]} is past. Review the track and move the date")
    if not nonblank(rc.get("title")):
        reasons.append("recipient title or verified responsibility must be stated")
    email = rc.get("email")
    dom = email_domain(email)
    if dom is None:
        reasons.append("recipient email must be a usable address")
    elif account_domain and dom != account_domain and not dom.endswith("." + account_domain):
        reasons.append("recipient domain does not match bundle account_domain")
    if rc.get("source") not in pol["recipient_sources"]:
        reasons.append("recipient source not in policy. Needs the seller to supply the address in this conversation")
    contact_id = rc.get("contact_id")
    if rc.get("source") == "existing Salesforce Contact with Email" and not nonblank(contact_id):
        reasons.append("Salesforce Contact recipient needs a nonempty contact_id")
    elif contact_id is not None and not nonblank(contact_id):
        reasons.append("recipient contact_id must be a nonempty string or null")
    account = p.get("account")
    if not isinstance(account, dict):
        reasons.append("current account ownership and opportunity facts are required")
    else:
        if not nonblank(account.get("id")) or domain(account.get("domain")) != account_domain:
            reasons.append("account identity must match the bundle")
        if b.get("salesforce_account_id") and account.get("id") != b["salesforce_account_id"]:
            reasons.append("account id must match the bundle")
        ab = b.get("adoption_bundle", {})
        if ab.get("salesforce_account_id") and account.get("id") != ab["salesforce_account_id"]:
            reasons.append("account id must match the adoption bundle")
        if account.get("owner_id") != common.load_policy(shared)["identity"]["sfdc_user_id"] or account.get("owner_is_active") is not True:
            reasons.append("account must be actively owned by the configured seller")
        if account.get("open_opportunity_ids") != []:
            reasons.append("account opportunity read must establish no open Opportunities")
    reads = p.get("reads")
    for name in ("tasks", "events", "gmail_sent"):
        receipt = reads.get(name) if isinstance(reads, dict) else None
        if not isinstance(receipt, dict) or receipt.get("complete") is not True:
            reasons.append(name + " requires a completed native-read receipt")
            continue
        if not nonblank(receipt.get("query_reference")):
            reasons.append(name + " needs its native query reference")
        stamp = common.parse_iso(receipt.get("checked_at"))
        if stamp is None or stamp > now or now - stamp > timedelta(hours=pol["bundle_checked_max_age_hours"]):
            reasons.append(name + " read is missing a fresh checked_at")
        if domain(receipt.get("account_domain")) != account_domain or norm(receipt.get("recipient_email") or "") != norm(email or ""):
            reasons.append(name + " read scope differs from the account and recipient")
        start = receipt.get("window_start")
        if not isinstance(start, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start) or d(start) > today - timedelta(days=pol["activity_lookback_days"]):
            reasons.append(name + " read window does not cover activity_lookback_days")
    # check 7
    cutoff = today - timedelta(days=pol["suppression_days"])
    me = {v.strip().lower() for v in (email, contact_id) if nonblank(v)}
    for a in act:
        if not isinstance(a, dict) or a.get("kind") not in ("task", "event", "gmail_sent"):
            raise ValueError("activity row needs kind task, event, or gmail_sent")
        activity_date = d(a.get("date"))
        if a["kind"] == "task" and (not nonblank(a.get("status")) or not nonblank(a.get("subtype"))):
            raise ValueError("activity task needs a nonempty status and subtype")
        who = a.get("who")
        if who is not None and not isinstance(who, str):
            raise ValueError("activity who must be a string or null")
        if nonblank(who) and not (email_domain(who) or re.fullmatch(r"(?:003|00Q)[A-Za-z0-9]+", who.strip(), re.I)):
            raise ValueError("activity who must be a Contact/Lead Id or email address, or blank when unknown")
        status = None
        if a["kind"] == "task":
            status = pol["task_status_map"].get(a["status"])
            if status not in ("completed", "open", "cancelled"):
                reasons.append("unmapped Task status: " + a["status"])
        done = a["kind"] in ("gmail_sent", "event") or (
            status == "completed" and a["subtype"] in pol["suppressing_task_subtypes"])
        mine = not nonblank(who) or who.strip().lower() in me
        if done and mine and activity_date >= cutoff:
            reasons.append(f"suppressed: {a['kind']} on {a['date']} to the recipient inside suppression window")
            break
    # check 8
    stray = sorted(numbers(strip_invite_minutes(body)) - numbers(b.get("quote")))
    if stray:
        reasons.append(f"numbers in body not in the bundle quote: {', '.join(stray)}")
    return reasons


def fit_flags(p, pol, shared):
    """Advisory capability review. Human review owns relevance and claim meaning."""
    meta = load_talk_track(shared)["meta"]
    match = VERIFY.search(p["draft"].get("body") or "")
    if meta.get("verify_before_action") and match:
        return [f"verify before action. Check current support for capability wording {match.group(1)!r}"]
    return []


def parse_now(s, policy):
    """Clock for the run. None means now in identity.timezone. A bare date means noon there. A naive timestamp is an error."""
    if not s:
        return common.policy_now(policy)
    t = common.parse_iso(s, policy)
    if t is None:
        raise ValueError(f"--now needs a date or an ISO timestamp with a timezone offset: {s!r}")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", required=True)
    ap.add_argument("--shared", default=str(SHARED))
    ap.add_argument("--now", "--today", dest="now", default=None,
                    help="ISO timestamp with offset, or a bare date meaning noon in identity.timezone. Defaults to now in that zone")
    a = ap.parse_args()
    try:
        shared = Path(a.shared)
        policy = common.load_policy(shared)
        pol = policy["outreach"]
        p = json.loads(Path(a.packet).read_text())
        reasons = check(p, pol, shared, parse_now(a.now, policy))
        flags = fit_flags(p, pol, shared)
    except common.INPUT_ERRORS as e:
        print(common.error_json(e))
        return 2
    if reasons:
        print(json.dumps({"verdict": "block", "reasons": reasons, "flags": flags}, indent=2))
        return 1
    print(json.dumps({"verdict": "allow", "recipient": p["recipient"]["email"], "signal_type": p["bundle"]["signal_type"],
                      "angle": p["talk_track"]["angle"], "pick_reason": p["talk_track"]["pick_reason"],
                      "persona": p["talk_track"]["persona"], "flags": flags}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
