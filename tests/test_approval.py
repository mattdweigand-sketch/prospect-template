"""Synthetic regression tests; no live services."""
import sys
import unittest

from gate_fixtures import SCRIPTS
sys.path.insert(0, str(SCRIPTS))
import approval  # noqa: E402


class ApprovalTests(unittest.TestCase):
    def test_hash_ignores_stamp_and_key_order(self):
        a = {"id": "x", "track": "t", "approved": {"date": "2026-09-22", "sha": "abc"}}
        b = {"track": "t", "id": "x"}
        self.assertEqual(approval.unit_hash(a), approval.unit_hash(b))
        self.assertEqual(len(approval.unit_hash(a)), 12)

    def test_any_field_change_changes_hash(self):
        base = {"id": "x", "track": "t", "limit": "l", "verticals": ["all"], "proof": {"name": "n", "external_ok": False}}
        h = approval.unit_hash(base)
        for k, v in (("track", "t2"), ("limit", "l2"), ("verticals", ["legal"]), ("proof", {"name": "n", "external_ok": True})):
            self.assertNotEqual(h, approval.unit_hash({**base, k: v}), k)

    def test_stamp_roundtrip(self):
        unit = {"id": "x", "track": "t"}
        st = approval.make_stamp(unit, "2026-09-22")
        unit["approved"] = st
        self.assertTrue(approval.stamp_current(unit, unit["approved"]))
        unit["track"] = "changed"
        self.assertFalse(approval.stamp_current(unit, unit["approved"]))
        self.assertFalse(approval.stamp_current(unit, None))
        self.assertFalse(approval.stamp_current(unit, {"sha": approval.unit_hash(unit)}))

    def test_date_object_and_string_hash_alike(self):
        import datetime
        a = {"id": "x", "when": datetime.date(2026, 9, 22)}
        b = {"id": "x", "when": "2026-09-22"}
        self.assertEqual(approval.unit_hash(a), approval.unit_hash(b))


if __name__ == "__main__":
    unittest.main()
