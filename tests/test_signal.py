"""Synthetic source-boundary checks, with no web access."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_signal import check


class SignalTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 11, tzinfo=timezone.utc)
        self.page = "On 2026-01-10 Example Account announced a new reporting initiative."
        self.bundle = {"account_name": "Example Account", "account_domain": "example.org",
                       "account_aliases": ["Example Account"], "signal_type": "reporting_initiative",
                       "source_url": "https://example.org/news", "quote": "Example Account announced a new reporting initiative.",
                       "quote_speaker": "account", "evidence_subject": "Example Account", "published_date": "2026-01-10",
                       "event_date": None, "checked_at": "2026-01-10T23:00:00Z"}
        self.taxonomy = {"signals": [{"id": "reporting_initiative", "tier": 1, "freshness_days": 90}]}

    def errors(self):
        return check(self.bundle, self.page, self.taxonomy, self.now)[0]

    def test_valid_quote_passes_structure_only(self):
        self.assertEqual(self.errors(), [])

    def test_invented_quote_rejected(self):
        self.bundle["quote"] = "This sentence was never on the page."
        self.assertTrue(self.errors())

    def test_expired_signal_rejected(self):
        self.bundle["published_date"] = "2024-01-01"
        self.assertTrue(self.errors())

    def test_naive_check_time_rejected(self):
        self.bundle["checked_at"] = "2026-01-10"
        self.assertTrue(self.errors())

    def test_future_dates_rejected(self):
        self.bundle["published_date"] = "2027-01-01"
        self.bundle["checked_at"] = "2027-01-01T00:00:00Z"
        self.assertEqual(len(self.errors()), 2)

    def test_undated_evergreen_rejected(self):
        self.bundle["published_date"] = None
        self.assertTrue(self.errors())

    def test_explicit_first_party_event_date_accepted(self):
        self.bundle["published_date"] = None
        self.bundle["event_date"] = "2026-01-10"
        self.assertEqual(self.errors(), [])

    def test_wrong_subject_rejected(self):
        self.bundle["evidence_subject"] = "Unrelated Account"
        self.assertTrue(self.errors())

    def test_third_party_attribution_is_visible(self):
        self.bundle["quote_speaker"] = "third_party"
        errors, warnings = check(self.bundle, self.page, self.taxonomy, self.now)
        self.assertFalse(errors)
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
