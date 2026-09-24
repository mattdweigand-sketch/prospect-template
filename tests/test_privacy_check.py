"""Synthetic regression tests; no live services."""
import json
import subprocess
import sys
import tempfile
import unittest

from gate_fixtures import SCRIPTS, SHARED
POLICY = SHARED / "policy.json"
sys.path.insert(0, str(SCRIPTS))
import privacy_check  # noqa: E402

CLEAN = {
    "account_name": "Example Account",
    "account_id": "account-1",
    "account_domain": "example.org",
    "data_through_date": "2026-09-20",
    "mapped_org_count": 1,
    "org_subscribed": True,
    "org_paying": True,
    "org_service_types": ["SELF_SERVE"],
    "org_platforms": ["stripe"],
    "paid_individuals_exist": True,
    "adoption": "org_adopted",
    "source_reference": "aggregate-query-1",
}


def run(bundle):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=SHARED) as f:
        json.dump(bundle, f)
    p = subprocess.run(
        [sys.executable, str(SCRIPTS / "privacy_check.py"), "--bundle", f.name, "--policy", str(POLICY)],
        capture_output=True, text=True,
    )
    return p.returncode, json.loads(p.stdout)


class PrivacyCheckTests(unittest.TestCase):
    def test_policy_keys_load(self):
        keys = privacy_check.load_policy(POLICY)
        self.assertEqual(set(keys), set(CLEAN))

    def test_clean_bundle_exits_0(self):
        code, out = run(CLEAN)
        self.assertEqual((code, out["verdict"]), (0, "clean"))

    def test_extra_key_blocked(self):
        code, out = run({**CLEAN, "user_count": 12})
        self.assertEqual(code, 1)
        self.assertIn("forbidden key: user_count", out["problems"])

    def test_missing_key_blocked(self):
        b = dict(CLEAN); del b["adoption"]
        code, out = run(b)
        self.assertEqual(code, 1)
        self.assertIn("missing key: adoption", out["problems"])

    def test_email_in_string_blocked(self):
        code, out = run({**CLEAN, "account_name": "jane.doe@example.org"})
        self.assertEqual(code, 1)
        self.assertIn("email address in account_name", out["problems"])

    def test_email_in_list_blocked(self):
        code, out = run({**CLEAN, "org_platforms": ["bob@example.org"]})
        self.assertEqual(code, 1)

    def test_timestamp_blocked(self):
        code, out = run({**CLEAN, "adoption": "org_adopted 2026-09-20 14:02"})
        self.assertEqual(code, 1)
        self.assertIn("timestamp in adoption", out["problems"])

    def test_bool_where_int_expected_blocked(self):
        code, out = run({**CLEAN, "mapped_org_count": True})
        self.assertEqual(code, 1)

    def test_wrong_type_blocked(self):
        code, out = run({**CLEAN, "org_paying": "yes"})
        self.assertEqual(code, 1)
        self.assertIn("wrong type for org_paying: expected bool", out["problems"])

    def test_bad_json_exits_2(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=SHARED) as f:
            f.write("{not json")
        p = subprocess.run([sys.executable, str(SCRIPTS / "privacy_check.py"), "--bundle", f.name], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
