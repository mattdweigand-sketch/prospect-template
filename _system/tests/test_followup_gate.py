import _support
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SHARED = _support.SHARED
SCRIPTS = ROOT / "_system" / "scripts"
sys.path.insert(0, str(ROOT / "_system" / "scripts"))
sys.path.insert(0, str(SCRIPTS))
import common  # noqa: E402
import followup_gate as fg  # noqa: E402

POLICY = common.load_policy()
SELLER = POLICY["identity"]["crm_user_id"]
TODAY = date(2026, 9, 21)

BASE = {
    "sent": [{"message_id": "m1", "is_sent": True, "thread_id": "t1", "subject": "Context engineering inside Example Buyer",
              "sent_at": "2026-09-21T14:05:00-07:00", "to": "jordan@buyer.example"}],
    "account": {"id": "001A", "owner_id": SELLER},
    "contacts": [{"id": "003A", "email": "Jordan@Buyer.example"}],
    "tasks": [{"id": "00T1", "subject": "LinkedIn - Connected", "description": ""}],
    "signal": {"signal_type": "relevant_leader_appointment", "unit": "Q2"},
}


def run(**over):
    p = copy.deepcopy(BASE)
    p.update(over)
    return fg.check(p, "standard", POLICY, today=TODAY)


class Allow(unittest.TestCase):
    def test_allow_fields(self):
        out = fg.check(copy.deepcopy(BASE), "standard", POLICY, today=TODAY)
        self.assertEqual(out["verdict"], "allow")
        t = out["task"]
        self.assertEqual(t["subject"], "Follow up: Context engineering inside Example Buyer")
        self.assertEqual(t["contact_id"], "003A")
        self.assertEqual(t["account_id"], "001A")
        self.assertEqual(t["owner_id"], SELLER)
        self.assertEqual(t["status"], "Not Started")
        self.assertEqual(t["subtype"], "Task")
        self.assertEqual(t["due_date"], "2026-09-28")
        self.assertIn("m1", t["description"])
        self.assertIn("t1", t["description"])
        self.assertIn("signal_type relevant_leader_appointment", t["description"])
        self.assertIn(" Q2.", t["description"])
        self.assertNotIn("completed_work", t["description"])
        self.assertNotIn("Type", t)

    def test_core_unit_allows(self):
        out = run(signal={"signal_type": "relevant_leader_appointment", "unit": "core.4"})
        self.assertEqual(out["verdict"], "allow")
        self.assertIn(" core.4.", out["task"]["description"])

    def test_historical_labels_survive_catalog_changes(self):
        out = run(signal={"signal_type": "retired_signal", "angle": "Previous approved angle"})
        self.assertEqual(out["verdict"], "allow")
        self.assertIn("Previous approved angle", out["task"]["description"])

    def test_missing_historical_labels_block(self):
        for signal in ({"signal_type": "", "angle": "Context"}, {"signal_type": "relevant_leader_appointment", "angle": " "}):
            out = run(signal=signal)
            self.assertEqual(out["verdict"], "block")

    def test_old_talk_track_id_key_is_not_read(self):
        out = run(signal={"signal_type": "relevant_leader_appointment", "talk_track_id": "Q2"})
        self.assertIn("signal angle must be a nonempty label from the approved outreach verdict", out["reasons"])

    def test_missing_signal_blocks(self):
        p = copy.deepcopy(BASE); del p["signal"]
        out = fg.check(p, "standard", POLICY, today=TODAY)
        self.assertEqual(out["verdict"], "block")

    def test_contact_email_case_insensitive(self):
        self.assertEqual(run()["verdict"], "allow")


class DueDate(unittest.TestCase):
    def test_pacific_date_from_utc(self):
        # 2026-09-22T05:30Z is still 2026-09-21 in Pacific
        d = fg.due_date("2026-09-22T05:30:00Z", "standard", POLICY)
        self.assertEqual(d.isoformat(), "2026-09-28")

    def test_arr_growth_mode_requires_arr_growth_ids(self):
        p = copy.deepcopy(BASE)
        out = fg.check(p, "arr_growth", POLICY, today=TODAY)
        self.assertTrue(any("arr_growth mode needs" in r for r in out["reasons"]))
        p["signal"] = {"signal_type": "arr_growth", "unit": "arr_growth"}
        out = fg.check(p, "arr_growth", POLICY, today=TODAY)
        self.assertEqual(out["verdict"], "allow")
        self.assertIn("signal_type arr_growth", out["task"]["description"])
        self.assertIn(" arr_growth.", out["task"]["description"])
        p["signal"] = {"signal_type": "arr_growth", "unit": "Q2"}
        out = fg.check(p, "arr_growth", POLICY, today=TODAY)
        self.assertIn("arr_growth mode needs signal_type and unit both arr_growth", out["reasons"])

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
        out = fg.check(p, "standard", POLICY, today=TODAY)
        self.assertEqual(out["verdict"], "block")


class Block(unittest.TestCase):
    def test_no_proof(self):
        out = run(sent=[])
        self.assertEqual(out["reasons"], ["no sent proof"])

    def test_ambiguous(self):
        out = run(sent=BASE["sent"] * 2)
        self.assertIn("ambiguous", out["reasons"][0])

    def test_missing_field(self):
        p = copy.deepcopy(BASE)
        del p["sent"][0]["subject"]
        self.assertEqual(fg.check(p, "standard", POLICY, today=TODAY)["reasons"], ["sent hit missing subject"])

    def test_missing_fields_accumulate_with_other_reasons(self):
        p = copy.deepcopy(BASE)
        del p["sent"][0]["subject"]
        del p["sent"][0]["to"]
        p["account"]["owner_id"] = "005OTHER"
        p["signal"]["unit"] = ""
        out = fg.check(p, "standard", POLICY, today=TODAY)
        self.assertEqual(out["verdict"], "block")
        self.assertIn("signal angle must be a nonempty label from the approved outreach verdict", out["reasons"])
        self.assertIn("sent hit missing subject", out["reasons"])
        self.assertIn("sent hit missing to", out["reasons"])
        self.assertIn("account owner is not identity.crm_user_id", out["reasons"])

    def test_wrong_owner(self):
        out = run(account={"id": "001A", "owner_id": "005OTHER"})
        self.assertIn("account owner is not identity.crm_user_id", out["reasons"])

    def test_zero_contacts(self):
        self.assertIn("contact match count 0, need exactly 1", run(contacts=[])["reasons"])

    def test_two_contacts(self):
        c = BASE["contacts"][0]
        self.assertIn("contact match count 2, need exactly 1", run(contacts=[c, dict(c, id="003B")])["reasons"])

    def test_contact_email_mismatch(self):
        out = run(contacts=[{"id": "003A", "email": "other@buyer.example"}])
        self.assertIn("contact email does not equal recipient", out["reasons"])

    def test_missing_or_unusable_contact_id_never_proposes_task(self):
        for value in (None, "", "  ", False, 12):
            out = run(contacts=[{"id": value, "email": "jordan@buyer.example"}])
            self.assertEqual(out["verdict"], "block")
            self.assertIn("contact needs a nonempty string id", out["reasons"])
            self.assertNotIn("task", out)
        out = run(contacts=[{"email": "jordan@buyer.example"}])
        self.assertIn("contact needs a nonempty string id", out["reasons"])

    def test_duplicate_by_subject(self):
        out = run(tasks=[{"id": "00T9", "subject": "Follow up: Context engineering inside Example Buyer", "description": ""}])
        self.assertEqual(out["reasons"], ["duplicate Task 00T9"])

    def test_duplicate_by_message_id(self):
        out = run(tasks=[{"id": "00T8", "subject": "anything", "description": "email provider message m1; thread t1."}])
        self.assertEqual(out["reasons"], ["duplicate Task 00T8"])

    def test_open_followup_task_blocks(self):
        out = run(tasks=[{"id": "00T7", "subject": "Follow up: check reply from Jordan", "description": "", "status": "Not Started"}])
        self.assertEqual(out["reasons"], ["open follow-up Task already exists 00T7"])

    def test_completed_followup_task_does_not_block(self):
        out = run(tasks=[{"id": "00T6", "subject": "Follow up: check reply from Jordan", "description": "", "status": "Completed"}])
        self.assertEqual(out["verdict"], "allow")

    def test_due_before_today_blocks(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-11T13:44:47-07:00"
        out = fg.check(p, "standard", POLICY, today=TODAY)
        self.assertIn("due date 2026-09-18 is before today", out["reasons"][0])

    def test_due_today_allows(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-14T10:00:00-07:00"
        self.assertEqual(fg.check(p, "standard", POLICY, today=TODAY)["verdict"], "allow")

    def test_multiple_reasons_reported(self):
        out = run(account={"id": "001A", "owner_id": "005OTHER"}, contacts=[])
        self.assertEqual(len(out["reasons"]), 2)


class TasksAndTimestamp(unittest.TestCase):
    def test_tasks_missing_blocks(self):
        p = copy.deepcopy(BASE); del p["tasks"]
        out = fg.check(p, "standard", POLICY, today=TODAY)
        self.assertEqual(out["verdict"], "block")
        self.assertTrue(any(r.startswith("tasks missing or not a list") for r in out["reasons"]))

    def test_tasks_null_blocks(self):
        out = run(tasks=None)
        self.assertEqual(out["verdict"], "block")
        self.assertTrue(any(r.startswith("tasks missing or not a list") for r in out["reasons"]))

    def test_tasks_wrong_type_blocks(self):
        out = run(tasks={"id": "00T1"})
        self.assertEqual(out["verdict"], "block")

    def test_tasks_empty_list_allows(self):
        self.assertEqual(run(tasks=[])["verdict"], "allow")

    def test_sent_at_later_today_blocks(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-21T18:00:00-07:00"
        now = datetime(2026, 9, 21, 14, 0, tzinfo=ZoneInfo(POLICY["identity"]["timezone"]))
        out = fg.check(p, "standard", POLICY, today=TODAY, now=now)
        self.assertEqual(out["verdict"], "block")
        self.assertIn("is after now", out["reasons"][0])

    def test_sent_at_earlier_today_allows(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-21T13:00:00-07:00"
        now = datetime(2026, 9, 21, 14, 0, tzinfo=ZoneInfo(POLICY["identity"]["timezone"]))
        self.assertEqual(fg.check(p, "standard", POLICY, today=TODAY, now=now)["verdict"], "allow")

    def test_sent_at_future_day_blocks(self):
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-25T09:00:00-07:00"
        out = fg.check(p, "standard", POLICY, today=TODAY)
        self.assertEqual(out["verdict"], "block")
        self.assertIn("is after now", out["reasons"][0])

    def test_sent_at_offset_compared_as_instant(self):
        # 22:00 UTC on the 21st is 15:00 Pacific. now is 14:00 Pacific, so it is in the future.
        p = copy.deepcopy(BASE)
        p["sent"][0]["sent_at"] = "2026-09-21T22:00:00Z"
        now = datetime(2026, 9, 21, 14, 0, tzinfo=ZoneInfo(POLICY["identity"]["timezone"]))
        self.assertEqual(fg.check(p, "standard", POLICY, today=TODAY, now=now)["verdict"], "block")

    def test_default_clock_is_policy_now(self):
        # 2026-09-29T04:00Z is 2026-09-28 21:00 Pacific. The due date 2026-09-28 is still today there, so it allows.
        fixed = datetime(2026, 9, 29, 4, 0, tzinfo=ZoneInfo("UTC"))
        with mock.patch.object(common, "policy_now", return_value=fixed.astimezone(common.policy_tz(POLICY))):
            self.assertEqual(fg.check(copy.deepcopy(BASE), "standard", POLICY)["verdict"], "allow")


class UnusableInput(unittest.TestCase):
    def test_account_null_is_input_error(self):
        with self.assertRaises(ValueError):
            run(account=None)

    def test_sent_not_a_list_is_input_error(self):
        with self.assertRaises(ValueError):
            run(sent={"message_id": "m1"})


class Cli(unittest.TestCase):
    def run_gate(self, packet, *extra):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "packet.json"
            f.write_text(json.dumps(packet))
            return subprocess.run([sys.executable, str(SCRIPTS / "followup_gate.py"), "--packet", str(f), "--today", "2026-09-21", *extra],
                                  capture_output=True, text=True)

    def test_exit_codes_and_envelopes(self):
        p = self.run_gate(BASE)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(json.loads(p.stdout)["verdict"], "allow")
        p = self.run_gate(dict(BASE, sent=[]))
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)["reasons"], ["no sent proof"])
        p = self.run_gate(dict(BASE, account=None))
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertEqual(p.stderr, "")
        out = json.loads(p.stdout)
        self.assertEqual(out["verdict"], "error")
        self.assertIn("account must be an object", out["reason"])
        p = self.run_gate(BASE, "--mode", "arr_growth")
        self.assertEqual(p.returncode, 1)

if __name__ == "__main__":
    unittest.main()
