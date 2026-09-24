"""Synthetic regression tests; no live services."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from gate_fixtures import SCRIPTS, SHARED
sys.path.insert(0, str(SCRIPTS))
import followup_gate as fg  # noqa: E402

POLICY = fg.load_policy(SHARED)
OWNER = POLICY["identity"]["owner_id"]
NOW = datetime.fromisoformat("2026-09-21T16:00:00-07:00")

BASE = {
    "tasks_complete": True, "contacts_complete": True, "sent_lookup_reference": "synthetic-sent-1",
    "sent": [{"message_id": "m1", "thread_id": "t1", "subject": "Context engineering inside Example Account",
              "sent_at": "2026-09-21T14:05:00-07:00", "to": "louis@example.org"}],
    "account": {"id": "account-1", "owner_id": OWNER, "open_opportunity_ids": []},
    "contacts": [{"id": "contact-1", "email": "Louis@Example.org", "account_id": "account-1"}],
    "tasks": [{"id": "00T1", "subject": "LinkedIn - Connected", "description": ""}],
    "signal": {"signal_type": "operations_leader_appointment", "claim_id": "report_delivery"},
}


def run(**over):
    p = copy.deepcopy(BASE)
    p.update(over)
    return fg.check(p, "standard", POLICY, now=NOW, shared=SHARED)


class Allow(unittest.TestCase):
    def test_allow_fields(self):
        out = fg.check(copy.deepcopy(BASE), "standard", POLICY, now=NOW, shared=SHARED)
        self.assertEqual(out["verdict"], "allow")
        t = out["task"]
        self.assertEqual(t["subject"], "Follow up: Context engineering inside Example Account")
        self.assertEqual(t["contact_id"], "contact-1")
        self.assertEqual(t["account_id"], "account-1")
        self.assertEqual(t["owner_id"], OWNER)
        self.assertEqual(t["status"], "Not Started")
        self.assertEqual(t["subtype"], "Task")
        self.assertEqual(t["due_date"], "2026-09-28")
        self.assertIn("m1", t["description"])
        self.assertIn("t1", t["description"])
        self.assertIn("signal_type operations_leader_appointment", t["description"])
        self.assertIn("claim_id report_delivery", t["description"])
        self.assertNotIn("Type", t)

    def test_unknown_signal_type_blocks(self):
        out = run(signal={"signal_type": "vibes", "claim_id": "report_delivery"})
        self.assertTrue(any("signal_type not a tier1 or tier2" in r for r in out["reasons"]))

    def test_unknown_claim_blocks(self):
        out = run(signal={"signal_type": "operations_leader_appointment", "claim_id": "nope"})
        self.assertTrue(any("claim_id not in claims.json" in r for r in out["reasons"]))

    def test_missing_signal_blocks(self):
        p = copy.deepcopy(BASE); del p["signal"]
        out = fg.check(p, "standard", POLICY, now=NOW, shared=SHARED)
        self.assertEqual(out["verdict"], "block")

    def test_contact_email_case_insensitive(self):
        self.assertEqual(run()["verdict"], "allow")


class DueDate(unittest.TestCase):
    def test_future_send_later_today_blocks_in_both_modes(self):
        for mode in ("standard", "arr_growth"):
            for sent in (NOW + timedelta(seconds=1), (NOW + timedelta(hours=1)).astimezone(timezone.utc)):
                with self.subTest(mode=mode, sent=sent):
                    p = copy.deepcopy(BASE)
                    p["sent"][0]["sent_at"] = sent.isoformat()
                    if mode == "arr_growth":
                        p["signal"] = {"signal_type": "arr_growth", "claim_id": "arr_growth"}
                    self.assertEqual(fg.check(p, mode, POLICY, NOW, SHARED)["reasons"], ["sent_at is in the future"])

    def test_send_at_current_instant_allows_across_offsets(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = NOW.astimezone(timezone.utc).isoformat()
        self.assertEqual(fg.check(p, "standard", POLICY, NOW, SHARED)["verdict"], "allow")

    def test_cli_uses_full_clock_and_rejects_naive_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packet.json"
            p = copy.deepcopy(BASE)
            p["sent"][0]["sent_at"] = (NOW + timedelta(seconds=1)).isoformat()
            path.write_text(json.dumps(p))
            cmd = [sys.executable, "-B", str(SCRIPTS / "followup_gate.py"), "--packet", str(path), "--shared", str(SHARED)]
            for clock, expected in ((NOW.isoformat(), 1), ("2026-09-21", 2), ("2026-09-21T16:00:00", 2)):
                with self.subTest(clock=clock):
                    result = subprocess.run(cmd + ["--now", clock], capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stdout)
                    self.assertNotEqual(json.loads(result.stdout)["verdict"], "allow")

    def test_pacific_date_from_utc(self):
        # 2026-09-22T05:30Z is still 2026-09-21 in Pacific
        d = fg.due_date("2026-09-22T05:30:00Z", "standard", POLICY)
        self.assertEqual(d.isoformat(), "2026-09-28")

    def test_arr_growth_mode_requires_arr_growth_ids(self):
        p = copy.deepcopy(BASE)
        out = fg.check(p, "arr_growth", POLICY, now=NOW, shared=SHARED)
        self.assertTrue(any("arr_growth mode needs" in r for r in out["reasons"]))
        p["signal"] = {"signal_type": "arr_growth", "claim_id": "arr_growth"}
        out = fg.check(p, "arr_growth", POLICY, now=NOW, shared=SHARED)
        self.assertEqual(out["verdict"], "allow")
        self.assertIn("signal_type arr_growth", out["task"]["description"])

    def test_arr_growth_skips_weekend(self):
        # Friday 2026-09-25 send. +2 weekdays = Tuesday 2026-09-29
        d = fg.due_date("2026-09-25T10:00:00-07:00", "arr_growth", POLICY)
        self.assertEqual(d.isoformat(), "2026-09-29")

    def test_arr_growth_midweek(self):
        d = fg.due_date("2026-09-21T10:00:00-07:00", "arr_growth", POLICY)
        self.assertEqual(d.isoformat(), "2026-09-23")

    def test_naive_timestamp_blocks(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-21T10:00:00"
        out = fg.check(p, "standard", POLICY, now=NOW, shared=SHARED)
        self.assertEqual(out["verdict"], "block")


class Block(unittest.TestCase):
    def test_missing_or_malformed_task_list_blocks_despite_complete_flag(self):
        missing = copy.deepcopy(BASE)
        missing.pop("tasks")
        cases = [missing] + [{**BASE, "tasks": value} for value in (None, False, {}, "", [None], ["task"])]
        for packet in cases:
            with self.subTest(tasks=packet.get("tasks", "missing")):
                result = fg.check(packet, "standard", POLICY, NOW, SHARED)
                self.assertEqual(result["verdict"], "block")
                self.assertIn("tasks must be an explicit list of task objects", result["reasons"])

    def test_explicit_empty_task_list_allows(self):
        self.assertEqual(run(tasks=[])["verdict"], "allow")

    def test_no_proof(self):
        out = run(sent=[])
        self.assertEqual(out["reasons"], ["no sent proof"])

    def test_ambiguous(self):
        out = run(sent=BASE["sent"] * 2)
        self.assertIn("ambiguous", out["reasons"][0])

    def test_missing_field(self):
        p = copy.deepcopy(BASE)
        del p["sent"][0]["thread_id"]
        self.assertEqual(fg.check(p, "standard", POLICY, now=NOW, shared=SHARED)["reasons"], ["sent hit missing thread_id"])

    def test_wrong_owner(self):
        out = run(account={"id": "account-1", "owner_id": "other-owner", "open_opportunity_ids": []})
        self.assertIn("account owner is not identity.owner_id", out["reasons"])

    def test_zero_contacts(self):
        self.assertIn("contact match count 0, need exactly 1", run(contacts=[])["reasons"])

    def test_two_contacts(self):
        c = BASE["contacts"][0]
        self.assertIn("contact match count 2, need exactly 1", run(contacts=[c, dict(c, id="contact-2")])["reasons"])

    def test_contact_email_mismatch(self):
        out = run(contacts=[{"id": "contact-1", "email": "other@example.org"}])
        self.assertIn("contact email does not equal recipient", out["reasons"])

    def test_duplicate_by_subject(self):
        out = run(tasks=[{"id": "00T9", "subject": "Follow up: Context engineering inside Example Account", "description": ""}])
        self.assertEqual(out["reasons"], ["duplicate Task 00T9"])

    def test_duplicate_by_message_id(self):
        out = run(tasks=[{"id": "00T8", "subject": "anything", "description": "Mail message m1; thread t1."}])
        self.assertEqual(out["reasons"], ["duplicate Task 00T8"])

    def test_open_followup_task_blocks(self):
        out = run(tasks=[{"id": "00T7", "subject": "Follow up: check reply from Louis", "description": "", "status": "Not Started"}])
        self.assertEqual(out["reasons"], ["open follow-up Task already exists 00T7"])

    def test_completed_followup_task_does_not_block(self):
        out = run(tasks=[{"id": "00T6", "subject": "Follow up: check reply from Louis", "description": "", "status": "Completed"}])
        self.assertEqual(out["verdict"], "allow")

    def test_due_before_today_blocks(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-11T13:44:47-07:00"
        out = fg.check(p, "standard", POLICY, now=NOW, shared=SHARED)
        self.assertIn("due date 2026-09-18 is before today", out["reasons"][0])

    def test_due_today_allows(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-14T10:00:00-07:00"
        self.assertEqual(fg.check(p, "standard", POLICY, now=NOW, shared=SHARED)["verdict"], "allow")

    def test_multiple_reasons_reported(self):
        out = run(account={"id": "account-1", "owner_id": "other-owner", "open_opportunity_ids": []}, contacts=[])
        self.assertEqual(len(out["reasons"]), 2)


if __name__ == "__main__":
    unittest.main()
