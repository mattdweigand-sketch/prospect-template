"""Synthetic regression tests; no live services."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from gate_fixtures import SHARED, make_shared
import factory
import refresh_tracks as rt  # noqa: E402

WATCH = ["customers", "learnings"]
IGNORE = ["index.md", "log.md"]


class RefreshTracksTests(unittest.TestCase):
    def test_committed_report_folds_whitespace_and_case(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shared = make_shared(root / "shared")
            source = root / "source"
            (source / "learnings").mkdir(parents=True)
            page = source / "learnings/a.md"
            page.write_text("Intro.\nSupplier  hands back\nfinished Work.\n")
            doc = factory.claim_document(shared)
            rows = doc["claims"][:3]
            for row, rid, ref, evidence in zip(rows, ("ok", "bad", "gone"),
                    ("./learnings/a.md", "learnings/a.md", "learnings/b.md"),
                    ("supplier hands back finished work.", "Supplier drafts work.", "x")):
                row.update(id=rid, source_reference=ref, evidence=evidence)
            doc.update(claims=rows, source_root="./")
            factory.write(shared / "claims.json", doc)
            rt.git(source, "init", "-q")
            rt.git(source, "add", ".")
            rt.git(source, "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "evidence")
            page.write_text("Dirty working tree is not evidence.")
            report = rt.report(source, shared)
            self.assertEqual([b["id"] for b in report["broken_rows"]], ["bad"])
            self.assertEqual([m["id"] for m in report["missing_pages"]], ["gone"])

    def test_changed_pages_filters_dirs_ignores_and_deletes(self):
        diff = "\0".join(("A", "knowledge/customers/example.md", "M", "knowledge/index.md", "M", "knowledge/systems/x.md",
                           "D", "knowledge/learnings/old.md", "M", "knowledge/learnings/customer-value-patterns.md", "M", "README.md", ""))
        out = rt.changed_pages(diff, "knowledge/", WATCH, IGNORE)
        self.assertEqual(out, [{"status": "added", "path": "customers/example.md"},
                               {"status": "deleted", "path": "learnings/old.md", "prior_revision": None,
                                "prior_path": "knowledge/learnings/old.md"},
                               {"status": "modified", "path": "learnings/customer-value-patterns.md"}])

    def test_nested_watch_normalization_deletion_and_rename_in_real_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shared = make_shared(root / "shared")
            source = root / "source"
            (source / "knowledge/products/nested").mkdir(parents=True)
            (source / "knowledge/products/nested-old").mkdir()
            doc = factory.claim_document(shared)
            doc["source_root"] = "./knowledge/"
            factory.write(shared / "claims.json", doc)
            (source / "knowledge/products/example.md").write_text("\n".join(row["evidence"] for row in doc["claims"]))
            for path in ("products/nested/old.md", "products/nested/former.md", "products/nested/ignored.md", "products/nested-old/outside.md", "policy.md"):
                (source / "knowledge" / path).write_text("Original content.\n")
            rt.git(source, "init", "-q")
            rt.git(source, "add", ".")
            rt.git(source, "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "baseline")
            previous = rt.git(source, "rev-parse", "HEAD")
            doc["source_revision"] = previous
            factory.write(shared / "claims.json", doc)
            policy = factory.read(shared / "policy.json")
            policy["refresh"].update(watch_dirs=["./products/nested/"], watch_paths=["./policy.md"], ignore_pages=["./products/nested/ignored.md"])
            factory.write(shared / "policy.json", policy)
            (source / "knowledge/products/nested/old.md").unlink()
            (source / "knowledge/products/nested/former.md").rename(source / "knowledge/products/nested/new.md")
            for path in ("products/nested/ignored.md", "products/nested-old/outside.md", "policy.md"):
                (source / "knowledge" / path).write_text("Changed content.\n")
            rt.git(source, "add", ".")
            rt.git(source, "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "changes")
            report = rt.report(source, shared)
            changes = {row["path"]: row for row in report["changed_pages"]}
            self.assertEqual(set(changes), {"policy.md", "products/nested/old.md", "products/nested/former.md", "products/nested/new.md"})
            self.assertEqual(changes["products/nested/new.md"]["status"], "added")
            for path in ("products/nested/old.md", "products/nested/former.md"):
                self.assertEqual(changes[path], {"status": "deleted", "path": path,
                    "prior_revision": previous, "prior_path": "knowledge/" + path})
            self.assertEqual(report["changed_watch_files"], ["policy.md"])
            self.assertFalse(report["missing_watch_pages"])
            rt.stamp(report, shared)
            self.assertEqual(factory.claim_document(shared)["source_revision"], report["head"])

    def test_git_path_records_preserve_unicode_quotes_and_backslashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shared = make_shared(root / "shared")
            source = root / "source"
            products = source / "knowledge/products"
            products.mkdir(parents=True)
            names = ["café.md", 'quote"name.md', "back\\slash.md"]
            doc = factory.claim_document(shared)
            doc["source_root"] = "knowledge"
            factory.write(shared / "claims.json", doc)
            (products / "example.md").write_text("\n".join(row["evidence"] for row in doc["claims"]))
            for name in names:
                (products / name).write_text("Original content.\n")
            policy = factory.read(shared / "policy.json")
            policy["refresh"].update(watch_dirs=["products"], watch_paths=["products/café.md"])
            factory.write(shared / "policy.json", policy)
            rt.git(source, "init", "-q")
            rt.git(source, "add", ".")
            rt.git(source, "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "path baseline")
            first = rt.report(source, shared)
            self.assertEqual({r["path"] for r in first["changed_pages"]},
                             {"products/" + name for name in names} | {"products/example.md"})
            self.assertTrue(all(r["status"] == "added" for r in first["changed_pages"]))
            previous = first["head"]
            for name in names:
                self.assertEqual(rt.page_at(source, previous, "knowledge", "products/" + name), "Original content.")
                (products / name).unlink()
                (products / ("new-" + name)).write_text("Replacement content.\n")
            doc["source_revision"] = previous
            factory.write(shared / "claims.json", doc)
            rt.git(source, "add", ".")
            rt.git(source, "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "path changes")
            report = rt.report(source, shared)
            changes = {row["path"]: row for row in report["changed_pages"]}
            self.assertEqual(set(changes), {"products/" + prefix + name for prefix in ("", "new-") for name in names})
            for name in names:
                self.assertEqual(changes["products/" + name], {"status": "deleted", "path": "products/" + name,
                    "prior_revision": previous, "prior_path": "knowledge/products/" + name})
                self.assertEqual(changes["products/new-" + name]["status"], "added")
            self.assertEqual(report["changed_watch_files"], ["products/café.md"])
            self.assertEqual(report["missing_watch_pages"], ["products/café.md"])

    def test_fixture_rows_all_have_evidence_and_source_reference(self):
        tt = json.loads((SHARED / "claims.json").read_text())
        for r in tt["claims"]:
            self.assertIn("evidence", r, r["id"])
            self.assertIn("source_reference", r, r["id"])
        for k in ("source_revision", "source_root", "evidence_verified", "held"):
            self.assertIn(k, tt)
        for k in ("angles_approval", "row_approval"):
            self.assertNotIn(k, tt)
        for r in tt["claims"]:
            for k in ("kind", "claim", "limit", "approved"):
                self.assertIn(k, r, r["id"])
            self.assertNotIn("angles", r, r["id"])

    def test_stamp_rewrites_meta_only(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(SHARED / "claims.json", Path(d) / "claims.json")
            before = json.loads((Path(d) / "claims.json").read_text())
            rt.stamp({"head": "abc1234", "head_date": "2026-10-01", "broken_rows": [], "missing_pages": []}, Path(d), today="2026-10-02")
            after = json.loads((Path(d) / "claims.json").read_text())
            self.assertEqual(after["source_revision"], "abc1234")
            self.assertEqual(str(after["source_date"]), "2026-10-01")
            self.assertEqual(str(after["evidence_verified"]), "2026-10-02")
            self.assertEqual(after["claims"], before["claims"])
            text = (Path(d) / "claims.json").read_text()
            self.assertEqual(json.loads(text), after)

    def test_changed_watch_files_needs_exact_path(self):
        diff = "\0".join(("M", "knowledge/analyses/enterprise-ideal-customer-profile.md", "M", "knowledge/contradictions.md",
                           "M", "knowledge/customers/contradictions.md", "D", "knowledge/analyses/other.md", "M", "contradictions.md", ""))
        out = rt.changed_watch_files(diff, "knowledge/", ["analyses/enterprise-ideal-customer-profile.md", "contradictions.md"])
        self.assertEqual(out, ["analyses/enterprise-ideal-customer-profile.md", "contradictions.md"])

    def test_contradiction_flags_match_open_entries_only(self):
        text = json.dumps({"schema_version": 1, "contradictions": [
            {"id": "scope-1", "status": "open", "summary": "Service availability differs.",
             "source_references": ["offers/service.md", "terms/coverage.md"]},
            {"id": "scope-2", "status": "resolved", "summary": "Previous scope clarified.",
             "source_references": ["cases/example.md"]}]})
        rows = [{"id": "service_catalog", "source_reference": "offers/service.md"},
                {"id": "report_delivery", "source_reference": "cases/example.md"},
                {"id": "regional_delivery", "source_reference": "terms/coverage.md"},
                {"id": "same_basename", "source_reference": "other/service.md"}]
        out = rt.contradiction_flags(text, rows)
        self.assertEqual(sorted(o["id"] for o in out), ["regional_delivery", "service_catalog"])
        self.assertEqual(out[0]["contradiction"], "Service availability differs.")
        self.assertEqual(out[0]["contradiction_id"], "scope-1")

    def test_invalid_contradiction_formats_never_look_empty(self):
        valid = {"id": "one", "status": "open", "summary": "Scope differs.", "source_references": ["offers/service.md"]}
        cases = ["", "# Open issues\nUnsupported Markdown.", "[]", "{}",
                 json.dumps({"schema_version": 2, "contradictions": []}),
                 json.dumps({"schema_version": True, "contradictions": []})]
        for entries in ([valid, valid], [{**valid, "status": "unknown"}], [{**valid, "summary": ""}],
                        [{**valid, "source_references": []}], [{**valid, "source_references": ["../outside.md"]}],
                        [{**valid, "source_references": ["offers/service.md", "offers/service.md"]}], [None]):
            cases.append(json.dumps({"schema_version": 1, "contradictions": entries}))
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                rt.contradiction_flags(text, [])
        self.assertEqual(rt.contradiction_flags('{"schema_version":1,"contradictions":[]}', []), [])

    def test_approve_rows_restamps_only_named_rows(self):
        import shutil
        import approval
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(SHARED / "claims.json", Path(d) / "claims.json")
            p = Path(d) / "claims.json"
            tt = json.loads(p.read_text())
            for r in tt["claims"]:
                if r["id"] in ("report_delivery", "account_context"):
                    r["track"] = "Changed."
            factory.write(p, tt)
            tt = json.loads(p.read_text())
            stale = [r["id"] for r in tt["claims"] if not approval.stamp_current(r, r.get("approved"))]
            self.assertEqual(stale, ["report_delivery", "account_context"])
            done = rt.approve_rows({"report_delivery"}, Path(d), today="2026-10-02")
            self.assertEqual(done, ["report_delivery"])
            tt = json.loads(p.read_text())
            stale = [r["id"] for r in tt["claims"] if not approval.stamp_current(r, r.get("approved"))]
            self.assertEqual(stale, ["account_context"])
            cw = next(r for r in tt["claims"] if r["id"] == "report_delivery")
            self.assertEqual(str(cw["approved"]["date"]), "2026-10-02")
            self.assertTrue(approval.stamp_current(cw, cw["approved"]))

    def test_approve_signals_and_persona_cares(self):
        import json
        import shutil
        import approval
        with tempfile.TemporaryDirectory() as d:
            for f in ("taxonomy.json", "icp.md"):
                shutil.copy(SHARED / f, Path(d) / f)
            jp = Path(d) / "taxonomy.json"
            t = json.loads(jp.read_text()); t["signals"][0]["freshness_days"] = 1
            jp.write_text(json.dumps(t, indent=2))
            sid = t["signals"][0]["id"]
            self.assertEqual(rt.approve_signals({sid}, Path(d), today="2026-10-02"), [sid])
            t = json.loads(jp.read_text())
            self.assertTrue(approval.stamp_current(t["signals"][0], t["signals"][0]["approved"]))
            self.assertEqual(t["signals"][0]["approved"]["date"], "2026-10-02")
            ip = Path(d) / "icp.md"
            ip.write_text(ip.read_text().replace("Decides how teams review repeatable work.", "Decides X.", 1))
            fm = json.loads(ip.read_text().split("---")[1])
            self.assertFalse(approval.stamp_current(fm["persona_cares"], fm["persona_cares_approved"]))
            rt.approve_persona_cares(Path(d), today="2026-10-02")
            fm = json.loads(ip.read_text().split("---")[1])
            self.assertTrue(approval.stamp_current(fm["persona_cares"], fm["persona_cares_approved"]))
            self.assertEqual(ip.read_text().count('"persona_cares_approved":'), 1)

    def test_unstamped_report_names_changed_units(self):
        import json
        tt = json.loads((SHARED / "claims.json").read_text())
        tax = json.loads((SHARED / "taxonomy.json").read_text())
        fm = json.loads((SHARED / "icp.md").read_text().split("---")[1])
        self.assertEqual(rt.unstamped(tt, tax, fm), [])
        tt["claims"][0]["claim"] = "edited"
        tax["signals"][3]["definition"] = "edited"
        fm["persona_cares"]["champion"] = "edited"
        out = rt.unstamped(tt, tax, fm)
        self.assertEqual([(o["unit"], o["id"]) for o in out],
                         [("row", tt["claims"][0]["id"]), ("signal", tax["signals"][3]["id"]), ("persona_cares", "icp.md")])


if __name__ == "__main__":
    unittest.main()
