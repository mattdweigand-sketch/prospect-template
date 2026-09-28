import _support
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = _support.SHARED
SCRIPTS = ROOT / "_system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import readback_check


class ReadbackTests(unittest.TestCase):
    def test_exact_email_fields_with_provider_metadata(self):
        proposal = {"to": "jane@example.com", "subject": "Question", "body": "Hello\n\nthe seller"}
        self.assertEqual("match", readback_check.compare(proposal, {**proposal, "id": "draft-1"})["verdict"])

    def test_changed_recipient_subject_or_complete_body(self):
        proposal = {"to": "jane@example.com", "subject": "Question", "body": "Hello\n\nthe seller"}
        for field in proposal:
            with self.subTest(field=field):
                actual = {**proposal, field: proposal[field] + " changed"}
                self.assertEqual([field], readback_check.compare(proposal, actual)["fields"])

    def test_missing_null_and_type_changes_are_not_matches(self):
        self.assertEqual("mismatch", readback_check.compare({"contact_id": None}, {})["verdict"])
        self.assertEqual("mismatch", readback_check.compare({"Enabled": True}, {"Enabled": 1})["verdict"])
        self.assertEqual("mismatch", readback_check.compare({"due_date": "2026-09-30"}, {"due_date": None})["verdict"])

    def test_nested_fields_and_order(self):
        self.assertEqual("mismatch", readback_check.compare({"record": {"Id": "001"}}, {"record": {"Id": "001", "type": "Account"}})["verdict"])
        self.assertEqual("mismatch", readback_check.compare({"to": ["a", "b"]}, {"to": ["b", "a"]})["verdict"])

    def test_empty_proposal_cannot_pass(self):
        with self.assertRaises(ValueError):
            readback_check.compare({}, {"Id": "001"})

    def test_email_rejects_added_copy_recipients_and_incomplete_proposal(self):
        proposal = {"to": "jane@example.com", "subject": "Question", "body": "Hello"}
        self.assertEqual("match", readback_check.compare(proposal, {**proposal, "id": "d1", "cc": [], "bcc": []}, email=True)["verdict"])
        for field in ("cc", "bcc", "CC", "Bcc"):
            for value in (["extra@example.com"], "extra@example.com", None):
                self.assertEqual("mismatch", readback_check.compare(proposal, {**proposal, field: value}, email=True)["verdict"])
        with self.assertRaises(ValueError):
            readback_check.compare({"to": "jane@example.com"}, proposal, email=True)

    def test_cli_match_mismatch_and_bad_input(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "expected.json"
            actual = Path(directory) / "actual.json"
            expected.write_text(json.dumps({"contact_id": "003A"}))
            for contents, code, verdict in [('{"contact_id":"003A"}', 0, "match"),
                                            ('{}', 1, "mismatch"),
                                            ('{"contact_id":NaN}', 2, "error")]:
                actual.write_text(contents)
                result = subprocess.run([sys.executable, str(SCRIPTS / "readback_check.py"),
                                         "--expected", str(expected), "--actual", str(actual)],
                                        capture_output=True, text=True)
                self.assertEqual(code, result.returncode, result.stderr)
                self.assertEqual(verdict, json.loads(result.stdout)["verdict"])


if __name__ == "__main__":
    unittest.main()
