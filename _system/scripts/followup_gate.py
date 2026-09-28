#!/usr/bin/env python3
"""Check one follow-up packet and emit canonical task fields to map and propose. signal-followup calls this once per send.

Usage:
    python3 _system/scripts/followup_gate.py --packet packet.json [--mode standard|arr_growth] [--today YYYY-MM-DD]
    --today is for tests. Default is today in identity.timezone.

packet.json
    {
      "sent": [ {"message_id": "...", "is_sent": true, "thread_id": "...", "subject": "...", "sent_at": "<aware ISO-8601>", "to": "x@acme.example"} ],   # live native messages with confirmed sent state
      "account": {"id": "account-123", "owner_id": "owner-123"},
      "contacts": [ {"id": "contact-123", "email": "x@acme.example"} ],                # Contacts on the Account whose Email matches the recipient
      "tasks": [ {"id": "task-123", "subject": "...", "description": "...", "status": "Not Started"} ],  # existing Tasks on the Contact, any status
      "signal": {"signal_type": "relevant_leader_appointment", "angle": "Implementation support"}   # from the outreach gate allow verdict in the thread. angle is the approved rationale label. arr_growth mode: both arr_growth
    }

Checks, in order. Every failing check names its reason. Checks 1 through 6 all run before the verdict. Check 7 runs
only when they pass.
    1. proof: exactly one sent hit. Zero is no proof. Two or more is ambiguous
    2. signal: signal_type and angle are nonempty historical labels from the approved outreach verdict, or both
       arr_growth in arr_growth mode. They land in Description. Do not revalidate a sent message against a
       subsequently edited content catalog. Legacy unit labels from existing sent messages are accepted
    3. sent fields: the hit carries message_id, subject, sent_at, to and native is_sent=true. thread_id is optional
    4. owner: account.owner_id equals identity.crm_user_id
    5. contact: exactly one contact with a nonempty string id, email equals sent.to case-insensitively
    6. duplicate: tasks must be a list (the live Task read, empty when the Contact has none). A missing or null
       tasks field blocks. No task whose subject equals the proposed Subject, whose description contains the
       message id, or which is open with a subject starting with the followup.task.subject prefix ("Follow up:")
    7. due date: sent_at is an aware timestamp not after now. identity.timezone send date + followup.due_calendar_days, or
       + arr_growth_due_business_days weekdays in arr_growth mode. Blocks when the due date is before today
       (--today overrides both today and now)

Exit 0 allow with the Task fields. Exit 1 block with reasons. Exit 2 unusable input, meaning a packet the checks cannot
read (not JSON, sent not a list, account not an object with id and owner_id). The exit 2 envelope is
{"verdict": "error", "reason": "..."}. Never a traceback. Always JSON on stdout.
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_system" / "scripts"))
from policy_templates import render, followup_description
import common  # noqa: E402

SHARED = common.SHARED


def due_date(sent_at, mode, policy):
    sent = common.parse_iso(sent_at)
    if sent is None:
        raise ValueError("sent_at needs a timezone")
    day = sent.astimezone(common.policy_tz(policy)).date()
    if mode == "standard":
        return day + timedelta(days=policy["followup"]["due_calendar_days"])
    remaining = policy["followup"]["arr_growth_due_business_days"]
    while remaining:
        day += timedelta(days=1)
        remaining -= day.weekday() < 5
    return day


def check(packet, mode, policy, today=None, now=None, shared=SHARED):
    if now is None:
        now = datetime.combine(today, datetime.max.time(), tzinfo=common.policy_tz(policy)) if today else common.policy_now(policy)
    today = today or now.date()
    fp = policy["followup"]
    reasons = []
    sent = packet.get("sent") or []
    acct = packet.get("account")
    if not isinstance(sent, list):
        raise ValueError("sent must be a list of native sent-message records")
    if not isinstance(acct, dict) or not common.opaque_id(acct.get("id")):
        raise ValueError("account must be an object with id and owner_id")
    if len(sent) == 0:
        return {"verdict": "block", "reasons": ["no sent proof"]}
    if len(sent) > 1:
        return {"verdict": "block", "reasons": [f"ambiguous: {len(sent)} plausible sent messages"]}
    s = sent[0]
    sig = packet.get("signal") or {}
    stype, unit = sig.get("signal_type"), sig.get("angle") or sig.get("unit")
    if mode == "arr_growth":
        if (stype, unit) != ("arr_growth", "arr_growth"):
            reasons.append("arr_growth mode needs signal_type and unit both arr_growth")
    else:
        for label, value in (("signal_type", stype), ("angle", unit)):
            if not isinstance(value, str) or not value.strip():
                reasons.append(f"signal {label} must be a nonempty label from the approved outreach verdict")
    if not isinstance(s, dict):
        raise ValueError("sent hit must be an object")
    for k in ("message_id", "subject", "sent_at", "to"):
        if not s.get(k):
            reasons.append(f"sent hit missing {k}")

    if s.get("is_sent") is not True:
        reasons.append("native sent state is not confirmed")
    if not common.opaque_id(s.get("message_id")):
        reasons.append("sent message_id must be an opaque ID")

    if acct.get("owner_id") != policy["identity"]["crm_user_id"]:
        reasons.append("account owner is not identity.crm_user_id")

    contacts = packet.get("contacts") or []
    if not isinstance(contacts, list):
        raise ValueError("contacts must be a list")
    if len(contacts) != 1:
        reasons.append(f"contact match count {len(contacts)}, need exactly 1")
    else:
        contact = contacts[0]
        if not isinstance(contact, dict):
            raise ValueError("contact must be an object")
        if not isinstance(contact.get("id"), str) or not contact["id"].strip():
            reasons.append("contact needs a nonempty string id")
        if (contact.get("email") or "").lower() != (s.get("to") or "").lower():
            reasons.append("contact email does not equal recipient")

    subject = render(fp["task"]["subject"], email_subject=s.get("subject") or "")
    prefix = fp["task"]["subject"].split("{")[0].strip()
    tasks = packet.get("tasks")
    if not isinstance(tasks, list):
        reasons.append("tasks missing or not a list. Read the Contact's Tasks and pass the list, empty when there are none")
        tasks = []
    for t in tasks:
        subj = t.get("subject") or ""
        is_open = (t.get("status") or "") not in fp["closed_statuses"]
        if subj == subject or (s.get("message_id") and s["message_id"] in (t.get("description") or "")):
            reasons.append(f"duplicate Task {t.get('id')}")
            break
        if is_open and subj.startswith(prefix):
            reasons.append(f"open follow-up Task already exists {t.get('id')}")
            break

    if reasons:
        return {"verdict": "block", "reasons": reasons}

    try:
        sent_ts = common.parse_iso(s["sent_at"])
        if sent_ts is None:
            raise ValueError("sent_at needs a timezone")
        due = due_date(s["sent_at"], mode, policy)
    except ValueError as e:
        return {"verdict": "block", "reasons": [str(e)]}
    if sent_ts > now:
        return {"verdict": "block", "reasons": [f"sent_at {s['sent_at']} is after now. Not a proven send"]}
    if due < today:
        return {"verdict": "block", "reasons": [f"due date {due.isoformat()} is before today. Send is older than the follow-up window"]}

    task = {
        "subject": subject,
        "account_id": acct["id"],
        "contact_id": contacts[0]["id"],
        "owner_id": policy["identity"]["crm_user_id"],
        "status": fp["task"]["status"],
        "priority": fp["task"]["priority"],
        "subtype": fp["task"]["subtype"],
        "due_date": due.isoformat(),
        "description": followup_description(fp["task"]["description"], message_id=s["message_id"], thread_id=s.get("thread_id") or "unavailable",
                                                        signal_type=stype, angle=unit),
    }
    return {"verdict": "allow", "mode": mode, "task": task}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", required=True)
    ap.add_argument("--mode", choices=("standard", "arr_growth"), default="standard")
    ap.add_argument("--shared", default=str(SHARED))
    ap.add_argument("--today", help="YYYY-MM-DD, tests only. Default is today in identity.timezone")
    a = ap.parse_args()
    try:
        shared = Path(a.shared)
        packet = json.loads(Path(a.packet).read_text())
        policy = common.load_policy(shared)
        out = check(packet, a.mode, policy, date.fromisoformat(a.today) if a.today else None, shared=shared)
    except common.INPUT_ERRORS as e:
        print(common.error_json(e))
        return 2
    print(json.dumps(out, indent=2))
    return 0 if out["verdict"] == "allow" else 1


if __name__ == "__main__":
    sys.exit(main())
