"""Synthetic regression tests; no live services."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from gate_fixtures import SCRIPTS, SHARED

import evidence_gate as gate

POLICY = SHARED / "policy.json"
TODAY = date(2026, 9, 21)
PAGE = ("Acme Corp today announced the appointment of Jane Doe as Chief Operating Officer.\n"
        "\u201cWe will deploy generative operations across every research workflow,\u201d Doe said.")


def receipt(**over):
    base = {"account_name": "Acme Corp", "account_aliases": ["Acme", "Jane Doe"], "account_domain": "example.org",
            "source_url": "https://example.org/news", "published_date": "2026-09-01",
            "quote": "appointment of Jane Doe as Chief Operating Officer", "evidence_subject": "Acme Corp",
            "signal_type": "operations_leader_appointment", "quote_speaker": "account"}
    base.update(over)
    return base


class EvidenceGate(unittest.TestCase):
    def setUp(self):
        self.scan, self.types = gate.load_taxonomy(POLICY)

    def run_gate(self, r, page=PAGE, today=TODAY):
        return gate.grade(r, page, self.scan, self.types, today)

    def test_qualified(self):
        code, out = self.run_gate(receipt())
        self.assertEqual(code, 0)
        self.assertEqual(out["bundle"]["tier"], "tier1")
        self.assertEqual(out["bundle"]["date_basis"], "published")
        self.assertNotIn("warnings", out["bundle"])

    def test_quote_with_curly_quotes_and_line_break_matches(self):
        r = receipt(quote='"We will deploy generative operations across every research workflow," Doe said.',
                    evidence_subject="Jane Doe")
        self.assertEqual(self.run_gate(r)[0], 0)

    def test_quote_not_in_page(self):
        code, out = self.run_gate(receipt(quote="Acme is buying Example Product next week"))
        self.assertEqual((code, out["reason"]), (1, "quote_not_in_page"))

    def test_quote_too_short(self):
        code, out = self.run_gate(receipt(quote="Chief Operating Officer"))
        self.assertEqual((code, out["reason"]), (1, "quote_too_short"))

    def test_subject_not_account_owned(self):
        code, out = self.run_gate(receipt(evidence_subject="Globex"))
        self.assertEqual((code, out["reason"]), (1, "evidence_subject_not_account_owned"))

    def test_alias_is_owned(self):
        self.assertEqual(self.run_gate(receipt(evidence_subject="acme"))[0], 0)

    def test_stale_by_signal_type_window(self):
        code, out = self.run_gate(receipt(published_date="2026-05-01"))
        self.assertEqual((code, out["reason"]), (1, "stale"))
        self.assertEqual(out["freshness_days"], 90)

    def test_tier3_never_qualifies(self):
        code, out = self.run_gate(receipt(signal_type="generic_marketing"))
        self.assertEqual((code, out["reason"]), (1, "tier3_never_qualifies"))

    def test_private_or_unconfigured_signal_source_cannot_qualify(self):
        code, out = self.run_gate(receipt(signal_type="paid_individuals_present"))
        self.assertEqual((code, out["reason"]), (1, "signal_source_not_web"))
        for source in (None, "", "warehouse"):
            with self.subTest(source=source):
                self.types["operations_leader_appointment"]["source"] = source
                code, out = self.run_gate(receipt())
                self.assertEqual((code, out["reason"]), (1, "signal_source_not_web"))

    def test_cli_dates_use_owner_timezone_independently_of_host(self):
        now = datetime.fromisoformat("2026-09-21T23:30:00-07:00")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(SHARED / "taxonomy.json", root / "taxonomy.json")
            (root / "page.txt").write_text(PAGE)
            for zone, owner_day in (("UTC", date(2026, 9, 22)), ("America/Los_Angeles", date(2026, 9, 21))):
                policy = json.loads(POLICY.read_text())
                policy["identity"]["timezone"] = zone
                (root / "policy.json").write_text(json.dumps(policy))
                for host in ("UTC", "Pacific/Honolulu"):
                    for age, expected in ((0, 0), (90, 0), (91, 1), (-1, 2)):
                        with self.subTest(zone=zone, host=host, age=age):
                            (root / "receipt.json").write_text(json.dumps(receipt(published_date=(owner_day - timedelta(days=age)).isoformat())))
                            result = subprocess.run([
                                sys.executable, "-B", str(SCRIPTS / "evidence_gate.py"),
                                "--receipt", str(root / "receipt.json"), "--page", str(root / "page.txt"),
                                "--policy", str(root / "policy.json"), "--now", now.isoformat(),
                                "--checked-at", (now - timedelta(minutes=1)).isoformat(),
                            ], env={**os.environ, "TZ": host}, capture_output=True, text=True)
                            self.assertEqual(result.returncode, expected, result.stdout)
                            output = json.loads(result.stdout)
                            if expected == 0:
                                self.assertEqual(output["bundle"]["checked_on"], owner_day.isoformat())
                            else:
                                self.assertEqual(output["reason"], "stale" if age == 91 else "published_date_in_future")

    def test_cli_replay_rejects_future_fetch_and_naive_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "receipt.json").write_text(json.dumps(receipt()))
            (root / "page.txt").write_text(PAGE)
            cmd = [sys.executable, "-B", str(SCRIPTS / "evidence_gate.py"),
                   "--receipt", str(root / "receipt.json"), "--page", str(root / "page.txt"),
                   "--policy", str(POLICY), "--checked-at", "2026-09-21T16:00:01-07:00"]
            for clock in ("2026-09-21T16:00:00-07:00", "2026-09-21T16:00:00", "2026-09-21"):
                with self.subTest(clock=clock):
                    result = subprocess.run(cmd + ["--now", clock], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertEqual(json.loads(result.stdout)["reason"], "input_error")

    def test_undated_page_without_event_date_fails(self):
        code, out = self.run_gate(receipt(published_date=None))
        self.assertEqual((code, out["reason"]), (1, "undated_page_without_event_date"))

    def test_undated_page_with_event_date_named_in_page(self):
        page = PAGE + "\nThe appointment takes effect Sept. 1, 2026."
        code, out = self.run_gate(receipt(published_date=None, event_date="2026-09-01"), page=page)
        self.assertEqual(code, 0)
        self.assertEqual(out["bundle"]["date_basis"], "page_event")
        self.assertEqual(out["bundle"]["published_date"], "2026-09-01")

    def test_undated_page_event_date_not_in_page_fails(self):
        code, out = self.run_gate(receipt(published_date=None, event_date="2026-09-01"))
        self.assertEqual((code, out["reason"]), (1, "event_date_not_in_page"))

    def test_undated_page_stale_event_fails(self):
        page = PAGE + "\nAnnounced 1 May 2026."
        code, out = self.run_gate(receipt(published_date=None, event_date="2026-05-01"), page=page)
        self.assertEqual((code, out["reason"]), (1, "stale"))

    def test_quote_speaker_required_and_constrained(self):
        code, out = self.run_gate(receipt(quote_speaker="vendor"))
        self.assertEqual((code, out["reason"]), (2, "quote_speaker_not_allowed"))

    def test_third_party_exec_statement_warns(self):
        r = receipt(signal_type="executive_statements", quote_speaker="third_party", evidence_subject="Jane Doe",
                    quote="We will deploy generative operations across every research workflow")
        code, out = self.run_gate(r)
        self.assertEqual(code, 0)
        self.assertEqual(out["bundle"]["warnings"], ["third_party_paraphrase"])

    def test_third_party_custom_signal_warns(self):
        self.types["reporting_initiative"] = {"tier": "tier1", "freshness_days": 90, "source": "web"}
        code, out = self.run_gate(receipt(signal_type="reporting_initiative", quote_speaker="third_party"))
        self.assertEqual(code, 0)
        self.assertEqual(out["bundle"]["warnings"], ["third_party_paraphrase"])

    def test_cli_rejects_naive_date_only_and_future_fetch_times(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "receipt.json").write_text(json.dumps(receipt()))
            (root / "page.txt").write_text(PAGE)
            for checked in (now.replace(tzinfo=None).isoformat(), now.date().isoformat(),
                            (now + timedelta(days=1)).isoformat()):
                with self.subTest(checked=checked):
                    result = subprocess.run([
                        sys.executable, "-B", str(SCRIPTS / "evidence_gate.py"),
                        "--receipt", str(root / "receipt.json"), "--page", str(root / "page.txt"),
                        "--policy", str(POLICY), "--checked-at", checked,
                    ], capture_output=True, text=True)
                    output = json.loads(result.stdout)
                    self.assertEqual((result.returncode, output["reason"]), (2, "input_error"))
                    self.assertIn("timezone-aware and not in the future", output["detail"])

    def test_future_date_unusable(self):
        code, out = self.run_gate(receipt(published_date="2026-10-01"))
        self.assertEqual((code, out["reason"]), (2, "published_date_in_future"))

    def test_unknown_signal_type_unusable(self):
        code, out = self.run_gate(receipt(signal_type="vibes"))
        self.assertEqual((code, out["reason"]), (2, "signal_type_not_in_taxonomy"))

    def test_missing_key_unusable(self):
        r = receipt()
        del r["account_aliases"]
        code, out = self.run_gate(r)
        self.assertEqual((code, out["reason"]), (2, "missing_keys"))


if __name__ == "__main__":
    unittest.main()
