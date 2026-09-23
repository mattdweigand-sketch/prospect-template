"""Synthetic regressions for review isolation, invalidation and exact result accounting."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import runs
import wrappers
import check_repo


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "output", "__pycache__"))
        for example in (self.root / "_shared").glob("*.example.*"):
            shutil.copyfile(example, example.with_name(example.name.replace(".example", "")))
        self.command = next(iter(wrappers.load_routes(self.root)))
        self.path = runs.init(self.root, "synthetic-001", self.command)

    def ready(self):
        (self.path / "01_review.md").write_text("---\nstatus: ready\n---\n\n# Synthetic review\n\n## Effect A1\nUnsent example draft to buyer@example.org.\n")

    def approve(self):
        return runs.record_review(self.root, self.path.name, "Synthetic reviewer", "test-only-approval", ["A1"])

    def result(self, review, effects=None):
        if effects is None:
            effects = [{"id": "A1", "status": "verified", "provider_reference": "synthetic-provider-1", "readback_reference": "synthetic-readback-1"}]
        (self.path / "02_result.json").write_text(json.dumps({"recorded_at": "2026-01-11T00:00:00Z", "summary": "Synthetic result; no service called", "review_snapshot": review["snapshot"], "effects": effects}))

    def test_starter_never_counts_as_ready(self):
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "draft")

    def test_run_ids_cannot_escape_or_overwrite(self):
        for bad in ("../escape", "UPPER", "x/y", ""):
            with self.assertRaises(ValueError):
                runs.init(self.root, bad, self.command)
        with self.assertRaises(ValueError):
            runs.init(self.root, self.path.name, self.command)

    def test_ready_requires_human_reference(self):
        self.ready()
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "awaiting_human_review")
        with self.assertRaises(ValueError):
            runs.record_review(self.root, self.path.name, "", "", [])

    def test_edit_invalidates_review(self):
        self.ready()
        self.approve()
        with (self.path / "01_review.md").open("a") as stream:
            stream.write("Changed recipient.\n")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_policy_edit_invalidates_review(self):
        self.ready()
        self.approve()
        policy = self.root / "_shared/policy.json"
        policy.write_text(policy.read_text() + "\n")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_declared_missing_artifact_prevents_review_record(self):
        self.ready()
        review = self.path / "01_review.md"
        review.write_text(review.read_text().replace("status: ready", 'status: ready\nartifacts: ["bundle.json"]'))
        with self.assertRaises(ValueError):
            self.approve()

    def test_changed_bundle_invalidates_review(self):
        self.ready()
        review = self.path / "01_review.md"
        review.write_text(review.read_text().replace("status: ready", 'status: ready\nartifacts: ["bundle.json"]'))
        bundle = self.path / "bundle.json"
        bundle.write_text('{"source": "synthetic"}')
        self.approve()
        bundle.write_text('{"source": "different"}')
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_run_cannot_declare_another_runs_input(self):
        self.ready()
        review = self.path / "01_review.md"
        review.write_text(review.read_text().replace("status: ready", 'status: ready\nartifacts: ["../other/bundle.json"]'))
        with self.assertRaises(ValueError):
            self.approve()

    def test_unsupported_or_duplicate_approval_rejected(self):
        self.ready()
        for ids in (["B2"], ["A1", "A1"]):
            with self.assertRaises(ValueError):
                runs.record_review(self.root, self.path.name, "Synthetic", "test", ids)

    def test_result_requires_provider_readback_reference(self):
        self.ready()
        review = self.approve()
        self.result(review, [{"id": "A1", "status": "verified", "provider_reference": "synthetic"}])
        with self.assertRaises(ValueError):
            runs.status(self.root, self.path.name)

    def test_unapproved_effect_not_accepted_in_result(self):
        self.ready()
        review = self.approve()
        self.result(review, [{"id": "B2", "status": "skipped"}])
        with self.assertRaises(ValueError):
            runs.status(self.root, self.path.name)

    def test_pending_result_is_incomplete(self):
        self.ready()
        review = self.approve()
        self.result(review, [{"id": "A1", "status": "pending"}])
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "incomplete")

    def test_complete_is_only_a_recorded_claim(self):
        self.ready()
        review = self.approve()
        self.result(review)
        state = runs.status(self.root, self.path.name)
        self.assertEqual(state["state"], "completion_recorded")
        self.assertIn("do not prove", state["note"])

    def test_another_run_cannot_supply_approval(self):
        self.ready()
        self.approve()
        other = runs.init(self.root, "synthetic-002", self.command)
        shutil.copyfile(self.path / "01_review.md", other / "01_review.md")
        shutil.copyfile(self.path / "review.json", other / "review.json")
        self.assertEqual(runs.status(self.root, other.name)["state"], "review_stale")

    def test_expected_configuration_change_is_not_unreviewed_drift(self):
        target = "_shared/policy.json"
        changed = (self.root / target).read_text() + "\n"
        after = {"A1": {target: hashlib.sha256(changed.encode()).hexdigest()}}
        (self.path / "01_review.md").write_text("---\nstatus: ready\nexpected_after: " + json.dumps(after) + "\n---\n\n## Effect A1\nReviewed synthetic policy revision.\n")
        review = self.approve()
        (self.root / target).write_text(changed)
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "recovery_required")
        self.result(review)
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "completion_recorded")

    def test_local_change_different_from_reviewed_postimage_is_stale(self):
        self.ready()
        self.approve()
        (self.root / "_shared/adapters.md").write_text("Different adapter\n")
        self.assertEqual(runs.status(self.root, self.path.name)["state"], "review_stale")

    def test_route_escape_rejected(self):
        contract = self.root / "scripts/wrapper-contract.json"
        doc = json.loads(contract.read_text())
        doc["commands"][self.command]["workflow"] = "workflows/../../outside.md"
        contract.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):
            wrappers.load_routes(self.root)

    def test_wrapper_drift_and_missing_target_detected(self):
        wrapper = self.root / f".agents/skills/{self.command}/SKILL.md"
        wrapper.write_text("not a pointer")
        self.assertTrue(wrappers.render(self.root, check=True))
        self.assertFalse(wrappers.render(self.root))
        self.assertFalse(wrappers.render(self.root, check=True))
        target = self.root / wrappers.load_routes(self.root)[self.command]["workflow"]
        target.unlink()
        with self.assertRaises(ValueError):
            wrappers.render(self.root, check=True)

    def test_factory_checks_pass_without_runtime_data(self):
        errors, _ = check_repo.check(self.root)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
