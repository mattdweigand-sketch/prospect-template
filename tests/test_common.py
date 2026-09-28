"""Run: python3 -m unittest discover -s tests"""
import _support
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SHARED = _support.SHARED
SCRIPTS = ROOT / "_shared" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import common  # noqa: E402

POLICY = common.load_policy(SHARED)
PACIFIC = ZoneInfo("America/Los_Angeles")


class FixedDatetime(datetime):
    """datetime whose now() is 2026-09-24 04:00 UTC, which is 2026-09-23 21:00 Pacific."""
    INSTANT = datetime(2026, 9, 24, 4, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.INSTANT.astimezone(tz) if tz else cls.INSTANT.replace(tzinfo=None)


def write_shared(d, policy_text, icp_text=None):
    (d / "policy.yaml").write_text(policy_text)
    if icp_text is not None:
        (d / "icp.md").write_text(icp_text)


class LoadersTests(unittest.TestCase):
    def test_shared_resolves_to_repo_shared_dir(self):
        self.assertEqual(common.SHARED, SHARED)

    def test_load_policy_reads_identity(self):
        self.assertEqual(POLICY["identity"]["timezone"], "America/Los_Angeles")
        self.assertTrue(POLICY["identity"]["sfdc_user_id"].startswith("005"))

    def test_load_policy_missing_dir_raises_oserror(self):
        with self.assertRaises(OSError):
            common.load_policy(Path("/nonexistent"))

    def test_icp_frontmatter_live_file(self):
        fm = common.icp_frontmatter(SHARED)
        self.assertTrue(set(fm) >= {"territory", "verticals", "disqualifiers"})
        self.assertLess(int(fm["territory"]["min_employees"]), int(fm["territory"]["max_employees"]))

    def test_icp_frontmatter_keeps_dashes_inside_values(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            write_shared(d, "identity: {}\n", "---\nterritory:\n  note: 'a --- b'\n  min_employees: 200\n---\n# ICP\n\n---\n\nBody rule with --- inside.\n")
            fm = common.icp_frontmatter(d)
        self.assertEqual(fm["territory"]["note"], "a --- b")
        self.assertEqual(fm["territory"]["min_employees"], 200)

    def test_icp_frontmatter_without_block_raises(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            write_shared(d, "identity: {}\n", "# ICP\nno frontmatter here\n")
            with self.assertRaises(ValueError):
                common.icp_frontmatter(d)

    def test_load_taxonomy_and_entry_lookup(self):
        tax = common.load_taxonomy(SHARED)
        entry, tier = common.taxonomy_entry(tax, "public_ai_initiative")
        self.assertEqual((entry["id"], tier), ("public_ai_initiative", "tier1"))
        entry, tier = common.taxonomy_entry(tax, "exec_ai_statements")
        self.assertEqual(tier, "tier2")
        self.assertEqual(common.taxonomy_entry(tax, "generic_ai_marketing"), (None, None))
        self.assertEqual(common.taxonomy_entry(tax, "vibes"), (None, None))

    def test_load_talk_track_live_file(self):
        tt = common.load_talk_track(SHARED)
        self.assertEqual(set(tt), {"meta", "body"})
        self.assertTrue(tt["meta"]["review_by"])
        self.assertIn("## Claim boundaries", tt["body"])
        self.assertNotIn("questions", tt["meta"])

    def test_load_talk_track_missing_dir_raises_oserror(self):
        with self.assertRaises(OSError):
            common.load_talk_track(Path("/nonexistent"))

    def test_taxonomy_types_covers_every_tier(self):
        tax = common.load_taxonomy(SHARED)
        types = common.taxonomy_types(tax)
        self.assertEqual(len(types), sum(len(v) for v in tax["tiers"].values()))
        self.assertEqual(types["generic_ai_marketing"]["tier"], "tier3")
        self.assertTrue(types["paid_individuals_present"]["source"].endswith(".sql"))
        self.assertIsNone(types["ai_exec_appointment"]["source"])
        self.assertEqual(types["ai_exec_appointment"]["freshness_days"], 90)


class ClockTests(unittest.TestCase):
    def setUp(self):
        self.old_tz = os.environ.get("TZ")
        os.environ["TZ"] = "UTC"
        time.tzset()

    def tearDown(self):
        if self.old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self.old_tz
        time.tzset()

    def test_policy_tz(self):
        self.assertEqual(str(common.policy_tz(POLICY)), "America/Los_Angeles")

    def test_policy_today_is_pacific_not_system_date(self):
        self.assertEqual(FixedDatetime.now(timezone.utc).date(), date(2026, 9, 24))   # the system UTC date
        with mock.patch.object(common, "datetime", FixedDatetime):
            self.assertEqual(common.policy_today(POLICY), date(2026, 9, 23))         # the policy date
            now = common.policy_now(POLICY)
        self.assertEqual(now.utcoffset(), datetime(2026, 9, 23, 21, tzinfo=PACIFIC).utcoffset())
        self.assertEqual(now, FixedDatetime.INSTANT)

    def test_policy_now_is_aware(self):
        self.assertIsNotNone(common.policy_now(POLICY).tzinfo)


class ParseIsoTests(unittest.TestCase):
    def test_z_suffix(self):
        self.assertEqual(common.parse_iso("2026-09-21T14:00:00Z"),
                         datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc))

    def test_offset(self):
        got = common.parse_iso("2026-09-21T14:00:00-07:00")
        self.assertEqual(got, datetime(2026, 9, 21, 21, 0, tzinfo=timezone.utc))

    def test_naive_is_none(self):
        self.assertIsNone(common.parse_iso("2026-09-21T14:00:00"))
        self.assertIsNone(common.parse_iso("2026-09-21T14:00:00", POLICY))

    def test_bare_date_without_policy_is_none(self):
        self.assertIsNone(common.parse_iso("2026-09-21"))

    def test_bare_date_with_policy_is_noon_in_policy_tz(self):
        got = common.parse_iso("2026-09-21", POLICY)
        self.assertEqual(got, datetime(2026, 9, 21, 12, 0, tzinfo=PACIFIC))
        self.assertEqual(got.utcoffset(), datetime(2026, 9, 21, tzinfo=PACIFIC).utcoffset())

    def test_garbage_and_empty_are_none(self):
        for bad in ("", None, "yesterday", "2026-13-01", 20260921):
            self.assertIsNone(common.parse_iso(bad), bad)


class ErrorEnvelopeTests(unittest.TestCase):
    def test_error_json_shape(self):
        out = json.loads(common.error_json(ValueError("bad thing")))
        self.assertEqual(out, {"verdict": "error", "reason": "ValueError: bad thing"})

    def test_input_errors_cover_the_usual_failures(self):
        for exc in (OSError(), ValueError(), KeyError(), TypeError(), AttributeError(),
                    json.JSONDecodeError("m", "d", 0), UnicodeDecodeError("utf-8", b"", 0, 1, "r")):
            self.assertIsInstance(exc, common.INPUT_ERRORS, type(exc))


if __name__ == "__main__":
    unittest.main()
