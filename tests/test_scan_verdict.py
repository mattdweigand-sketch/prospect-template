"""Synthetic regression tests; no live services."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from gate_fixtures import SCRIPTS

HERE = Path(__file__).resolve().parent
SCRIPT = SCRIPTS / "scan_verdict.py"
spec = importlib.util.spec_from_file_location("scan_verdict", SCRIPT)
sv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sv)


def q(tier, date, stype="ai_hiring_cluster"):
    return {"outcome": "qualified", "bundle": {"tier": tier, "published_date": date, "signal_type": stype,
        "gate": "evidence_gate", "account_name": "Example Account", "account_aliases": ["Example"],
        "account_domain": "example.org", "source_url": "https://example.org/news", "quote": "The team announced its reporting initiative.",
        "evidence_subject": "Example Account", "quote_speaker": "account", "date_basis": "published", "event_date": None,
        "checked_on": "2026-09-21", "checked_at": "2026-09-21T12:00:00+00:00"}}


NO = {"outcome": "no_usable_signal", "reason": "quote_not_in_page"}


class ScanVerdict(unittest.TestCase):
    def test_nothing_qualified_stops(self):
        v = sv.verdict([NO, NO])
        self.assertEqual(v["checked"], 2)
        self.assertIsNone(v["recommended"])
        self.assertEqual(v["next"], "Stop")
        self.assertIn("Not proof of absence", v["verdict"])

    def test_one_tier2_is_a_reason_to_reach_out(self):
        v = sv.verdict([NO, q("tier2", "2026-08-27"), NO])
        self.assertEqual(v["recommended"], 2)
        self.assertEqual(v["verdict"], "Signal 2 qualified.")
        self.assertEqual(v["next"], "signal-outreach with Signal 2")

    def test_tier1_beats_newer_tier2(self):
        v = sv.verdict([q("tier2", "2026-09-20"), q("tier1", "2026-08-01")])
        self.assertEqual(v["recommended"], 2)

    def test_newest_within_tier_wins(self):
        v = sv.verdict([q("tier1", "2026-08-01"), q("tier1", "2026-09-10"), q("tier1", "2026-09-10")])
        self.assertEqual(v["recommended"], 2)  # tie on date goes to the lower number

    def test_invalid_dates_and_envelopes_are_unusable(self):
        cases = [[], None, {}, {"outcome": "invented"}, {"outcome": "unusable"}]
        cases += [q("tier1", value) for value in (None, "not-a-date", "2026-9-01", "2026-02-30", "😀")]
        cases += [{"outcome": "qualified", "bundle": value} for value in (None, [], {})]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(sv.verdict([case])["outcome"], "unusable")

    def test_partial_bundle_cannot_be_a_qualified_result(self):
        for field in q("tier1", "2026-09-20")["bundle"]:
            item = q("tier1", "2026-09-20")
            del item["bundle"][field]
            with self.subTest(field=field):
                self.assertEqual(sv.verdict([item])["outcome"], "unusable")

    def test_declared_input_failure_remains_a_coverage_limitation(self):
        finding = sv.verdict([{"outcome": "unusable", "reason": "input_error"}, NO])
        self.assertEqual(finding["checked"], 2)
        self.assertIsNone(finding["recommended"])

    def test_qualified_without_tier_is_unusable(self):
        v = sv.verdict([{"outcome": "qualified", "bundle": {}}])
        self.assertEqual(v["outcome"], "unusable")

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i, o in enumerate([NO, q("tier2", "2026-08-27")]):
                p = Path(d) / f"g{i}.json"
                p.write_text(json.dumps(o))
                paths.append(str(p))
            r = subprocess.run([sys.executable, str(SCRIPT), *paths], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(out["next"], "signal-outreach with Signal 2")
            r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            r = subprocess.run([sys.executable, str(SCRIPT), str(Path(d) / "missing.json")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(json.loads(r.stdout)["reason"], "unreadable_gate_output")
            invalid = Path(d) / "invalid.json"
            for value in ([], q("tier1", "😀"), q("tier1", "2026-9-01")):
                invalid.write_text(json.dumps(value))
                r = subprocess.run([sys.executable, "-B", str(SCRIPT), str(invalid)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(json.loads(r.stdout)["outcome"], "unusable")
                self.assertEqual(r.stderr, "")
            invalid.write_bytes(b"\xff")
            r = subprocess.run([sys.executable, "-B", str(SCRIPT), str(invalid)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(json.loads(r.stdout)["reason"], "unreadable_gate_output")


if __name__ == "__main__":
    unittest.main()
