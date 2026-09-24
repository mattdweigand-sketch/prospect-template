"""Git checkout/export enumeration regressions; no live services."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from gate_fixtures import ROOT
import check_repo


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


class RepositoryEnumerationTests(unittest.TestCase):
    def test_tracked_private_file_is_rejected_in_checkout_and_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "checkout"
            checkout.mkdir()
            for rel in check_repo.public_files(ROOT):
                destination = checkout / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, destination)
            git(checkout, "init", "-q")
            private = checkout / "_shared/policy.json"
            private.write_text("{}\n")
            git(checkout, "add", ".")
            git(checkout, "add", "-f", "_shared/policy.json")
            git(checkout, "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "fixture")
            worktree = Path(directory) / "linked"
            git(checkout, "worktree", "add", "--detach", str(worktree), "HEAD")
            self.assertTrue((worktree / ".git").is_file())
            for root in (checkout, worktree):
                with self.subTest(root=root):
                    self.assertIn(Path("_shared/policy.json"), check_repo.public_files(root))
                    errors, _ = check_repo.check(root)
                    self.assertIn("deployment or runtime material included: _shared/policy.json", errors)

    def test_export_inside_parent_checkout_does_not_enumerate_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            git(parent, "init", "-q")
            (parent / "parent-only.md").write_text("Outside the export.\n")
            export = parent / "export"
            export.mkdir()
            (export / "AGENTS.md").write_text("Export entry.\n")
            self.assertEqual(check_repo.public_files(export), [Path("AGENTS.md")])

    def test_non_git_export_still_works_without_git_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("Export entry.\n")
            with patch.object(check_repo.subprocess, "run", side_effect=FileNotFoundError):
                self.assertEqual(check_repo.public_files(root), [Path("AGENTS.md")])


if __name__ == "__main__":
    unittest.main()
