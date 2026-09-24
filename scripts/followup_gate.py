#!/usr/bin/env python3
"""Check a proven send and render one normalized open follow-up task.

Usage: python3 scripts/followup_gate.py --packet FILE [--mode standard|arr_growth] [--shared DIR]
Packet:
  sent: exactly one {message_id, thread_id, subject, sent_at: aware ISO, to}.
  sent_lookup_reference: completed live sent-mail lookup receipt.
  account: {id, owner_id, open_opportunity_ids: []}.
  contacts: exactly one {id, account_id, email} matching the account and send.
  contacts_complete: true; tasks_complete: true, backed by complete read receipts.
  tasks: required list of all contact tasks [{id, subject, description, status}], any status.
    An empty list means a completed lookup found none; missing/null blocks.
    Each task needs nonblank ID/subject/status and a string description (empty is
    allowed). An unfamiliar nonblank status is conservatively open.
  signal: {signal_type, claim_id} from the reviewed handoff; both arr_growth for
    arr_growth mode. Missing attribution is not guessed.

Checks proof uniqueness, owner/open deal, contact association, duplicate subject,
message ID and open follow-up prefix; calculates the configured calendar/weekday
cadence in the owner's timezone. Due dates before today and future sends block,
including a timestamp later today. --now accepts an aware timestamp for replay.
Normalized task fields must be mapped to exact provider fields before review.
No completed-email logging, provider calls or writes. Exit 0 allow, 1 block,
2 unusable input. Full lifecycle: workflows/outreach/signal-followup.md.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import factory

SHARED = Path(__file__).resolve().parents[1] / "_shared"


def load_policy(shared=SHARED):
    return factory.read(shared / "policy.json")


def due_date(sent_at, mode, policy):
    factory.validate_policy(policy, ("identity", "followup_signal"))
    if mode not in ("standard", "arr_growth"):
        raise ValueError("unknown follow-up mode")
    sent = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
    if sent.tzinfo is None:
        raise ValueError("sent_at needs a timezone")
    day = sent.astimezone(ZoneInfo(policy["identity"]["timezone"])).date()
    remaining = policy["followup_signal"]["due_calendar_days" if mode == "standard" else "growth_due_business_days"]
    if type(remaining) is not int or remaining < 0:
        raise ValueError("cadence must be a nonnegative integer")
    if mode == "standard":
        return day + timedelta(days=remaining)
    while remaining:
        day += timedelta(days=1)
        remaining -= day.weekday() < 5
    return day


def validate_packet(packet):
    factory.require(isinstance(packet, dict), "packet must be an object")
    account = packet.get("account")
    factory.require(isinstance(account, dict), "account must be an object")
    for key in ("id", "owner_id"):
        factory.require(factory.nonblank(account.get(key)), f"account.{key} must be a nonblank string")
    opportunities = account.get("open_opportunity_ids")
    factory.require(isinstance(opportunities, list) and all(factory.nonblank(v) for v in opportunities),
                    "account.open_opportunity_ids must be a list of nonblank strings")
    for section, keys in (("sent", ("message_id", "thread_id", "subject", "sent_at", "to")),
                          ("contacts", ("id", "account_id", "email")), ("tasks", ("id", "subject", "status"))):
        items = packet.get(section)
        factory.require(isinstance(items, list), f"{section} must be an explicit list of objects")
        for item in items:
            factory.require(isinstance(item, dict), f"{section} entries must be objects")
            for key in keys:
                factory.require(factory.nonblank(item.get(key)), f"{section}.{key} must be a nonblank string")
            if section == "tasks":
                factory.require(isinstance(item.get("description"), str), "tasks.description must be a string")
            else:
                factory.email(item["to" if section == "sent" else "email"])
    signal = packet.get("signal")
    factory.require(signal is None or isinstance(signal, dict), "signal must be an object")
    for key in ("signal_type", "claim_id"):
        value = (signal or {}).get(key)
        factory.require(value is None or isinstance(value, str), f"signal.{key} must be a string or null")


def check(packet, mode, policy, now=None, shared=SHARED):
    factory.validate_policy(policy, ("identity", "followup_signal"))
    factory.require(mode in ("standard", "arr_growth"), "unknown follow-up mode")
    validate_packet(packet)
    zone = ZoneInfo(policy["identity"]["timezone"])
    now = now or datetime.now(zone)
    if now.tzinfo is None:
        raise ValueError("now must be a timezone-aware timestamp")
    today = now.astimezone(zone).date()
    fp = policy["followup_signal"]
    reasons = []
    if packet.get("tasks_complete") is not True or packet.get("contacts_complete") is not True or not factory.nonblank(packet.get("sent_lookup_reference")):
        reasons.append("complete contact/task reads and live sent-mail reference are required")
    tasks = packet["tasks"]
    sent = packet["sent"]
    if len(sent) == 0:
        return {"verdict": "block", "reasons": ["no sent proof"]}
    if len(sent) > 1:
        return {"verdict": "block", "reasons": [f"ambiguous: {len(sent)} plausible sent messages"]}
    s = sent[0]
    sig = packet.get("signal") or {}
    stype, track = sig.get("signal_type"), sig.get("claim_id")
    if mode == "arr_growth":
        if (stype, track) != ("arr_growth", "arr_growth"):
            reasons.append("arr_growth mode needs signal_type and claim_id both arr_growth")
    else:
        tax = factory.taxonomy(shared)["tiers"]
        if stype not in {t["id"] for tier in ("tier1", "tier2") for t in tax[tier]}:
            reasons.append(f"signal_type not a tier1 or tier2 taxonomy id: {stype}")
        tracks = {t["id"] for t in factory.claim_document(shared)["claims"]}
        if track not in tracks:
            reasons.append(f"claim_id not in claims.json: {track}")
    if packet.get("account", {}).get("owner_id") != policy["identity"]["owner_id"]:
        reasons.append("account owner is not identity.owner_id")
    if packet.get("account", {}).get("open_opportunity_ids") != []:
        reasons.append("account must have a verified empty open-opportunity list")

    contacts = packet["contacts"]
    if len(contacts) != 1:
        reasons.append(f"contact match count {len(contacts)}, need exactly 1")
    elif factory.email(contacts[0]["email"]) != factory.email(s["to"]):
        reasons.append("contact email does not equal recipient")
    elif contacts[0].get("account_id") != packet["account"].get("id") or not contacts[0].get("id"):
        reasons.append("contact must belong to the resolved account")

    subject = fp["task"]["subject"].format(mail_subject=s["subject"])
    prefix = fp["task"]["subject"].split("{")[0].strip()
    for t in tasks:
        subj = t["subject"]
        is_open = t["status"] not in fp["closed_statuses"]
        if subj == subject or s["message_id"] in t["description"]:
            reasons.append(f"duplicate Task {t.get('id')}")
            break
        if is_open and subj.startswith(prefix):
            reasons.append(f"open follow-up Task already exists {t.get('id')}")
            break

    if reasons:
        return {"verdict": "block", "reasons": reasons}

    try:
        due = due_date(s["sent_at"], mode, policy)
        if datetime.fromisoformat(s["sent_at"].replace("Z", "+00:00")) > now:
            raise ValueError("sent_at is in the future")
    except ValueError as e:
        return {"verdict": "block", "reasons": [str(e)]}
    if due < today:
        return {"verdict": "block", "reasons": [f"due date {due.isoformat()} is before today. Send is older than the follow-up window"]}

    task = {
        "subject": subject,
        "account_id": packet["account"]["id"],
        "contact_id": contacts[0]["id"],
        "owner_id": policy["identity"]["owner_id"],
        "status": fp["task"]["status"],
        "priority": fp["task"]["priority"],
        "subtype": fp["task"]["subtype"],
        "due_date": due.isoformat(),
        "description": fp["task"]["description"].format(message_id=s["message_id"], thread_id=s["thread_id"],
                                                        signal_type=stype, claim_id=track),
    }
    return {"verdict": "allow", "mode": mode, "task": task}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", required=True)
    ap.add_argument("--mode", choices=("standard", "arr_growth"), default="standard")
    ap.add_argument("--now", help="Timezone-aware timestamp for deterministic replay; defaults to the current time")
    ap.add_argument("--shared", type=Path, default=SHARED)
    a = ap.parse_args()
    try:
        packet = json.loads(Path(a.packet).read_text())
        policy = load_policy(a.shared)
        now = datetime.fromisoformat(a.now.replace("Z", "+00:00")) if a.now else None
        out = check(packet, a.mode, policy, now, a.shared)
    except Exception as e:
        print(json.dumps({"verdict": "error", "reasons": [str(e)]}))
        return 2
    print(json.dumps(out, indent=2))
    return 0 if out["verdict"] == "allow" else 1


if __name__ == "__main__":
    sys.exit(main())
