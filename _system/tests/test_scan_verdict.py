"""Run: python3 -m unittest discover -s _system/tests"""
import _support
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = _support.SHARED
SCRIPTS = ROOT / "_system" / "scripts"
sys.path.insert(0, str(ROOT / "_system" / "scripts"))
SCRIPT = SCRIPTS / "scan_verdict.py"
sys.path.insert(0, str(SCRIPTS))
import scan_verdict as sv  # noqa: E402


def q(tier, date, stype="relevant_hiring_cluster"):
    return {"outcome": "qualified", "bundle": {"tier": tier, "published_date": date, "signal_type": stype,
        "classification": "active_initiative", "relevance": "relevant_to_offer", "fit_reason": "The evidenced initiative matches the configured offer and its stated limits."}}


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

    def test_legacy_or_api_bundle_cannot_recommend_outreach(self):
        for change in ({"classification": None}, {"classification": "early_indication"}, {"relevance": "outside_offer"}):
            output = q("tier1", "2026-09-24")
            output["bundle"].update(change)
            self.assertEqual(sv.verdict([output])["reason"], "qualified_bundle_without_active_relevant_to_offer")

    def test_missing_date_sorts_last(self):
        v = sv.verdict([q("tier1", None), q("tier1", "2026-07-01")])
        self.assertEqual(v["recommended"], 2)

    def test_qualified_without_tier_is_unusable(self):
        v = sv.verdict([{"outcome": "qualified", "bundle": {}}])
        self.assertEqual(v["outcome"], "unusable")

    def test_malformed_qualified_bundle_returns_named_cli_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "gate.json"
            p.write_text(json.dumps({"outcome": "qualified", "bundle": ["not an object"]}))
            r = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stderr, "")
        self.assertEqual(json.loads(r.stdout)["reason"], "qualified_bundle_not_object")

    def test_malformed_tier_or_date_is_unusable(self):
        self.assertEqual(sv.verdict([q([], "2026-09-24")])["reason"], "qualified_bundle_without_tier")
        for invalid in ([], "tomorrow", "2026-02-30"):
            self.assertEqual(sv.verdict([q("tier1", invalid)])["reason"], "qualified_bundle_invalid_date")

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
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["next"], "Stop")
            r = subprocess.run([sys.executable, str(SCRIPT), str(Path(d) / "missing.json")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(json.loads(r.stdout)["reason"], "unreadable_gate_output")

    def test_help_exits_0(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("gate_output.json", r.stdout)

    def test_non_utf8_file_is_unusable_not_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_bytes(b"\xff\xfe\x00bad")
            r = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stderr, "")
        out = json.loads(r.stdout)
        self.assertEqual((out["outcome"], out["reason"]), ("unusable", "unreadable_gate_output"))

    def test_main_returns_exit_code(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(sv.main([]), 0)
        self.assertEqual(json.loads(buf.getvalue())["next"], "Stop")


if __name__ == "__main__":
    unittest.main()
