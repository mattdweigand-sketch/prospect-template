"""Synthetic regression tests; no live services."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from gate_fixtures import SHARED
import refresh_tracks as rt  # noqa: E402

WATCH = ["customers", "learnings"]
IGNORE = ["index.md", "log.md"]


class RefreshTracksTests(unittest.TestCase):
    def test_verify_rows_folds_whitespace_and_case(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "learnings").mkdir()
            (Path(d) / "learnings" / "a.md").write_text("Intro.\nSupplier  hands back\nfinished Work.\n")
            rows = [{"id": "ok", "source_reference": "learnings/a.md", "evidence": "supplier hands back finished work."},
                    {"id": "bad", "source_reference": "learnings/a.md", "evidence": "Supplier drafts work."},
                    {"id": "gone", "source_reference": "learnings/b.md", "evidence": "x"}]
            broken, missing = rt.verify_rows(rows, d)
            self.assertEqual([b["id"] for b in broken], ["bad"])
            self.assertEqual([m["id"] for m in missing], ["gone"])

    def test_changed_pages_filters_dirs_ignores_and_deletes(self):
        diff = "A\tknowledge/customers/example.md\nM\tknowledge/index.md\nM\tknowledge/systems/x.md\nD\tknowledge/learnings/old.md\nM\tknowledge/learnings/customer-value-patterns.md\nR100\tknowledge/customers/a.md\tknowledge/customers/b.md\nM\tREADME.md"
        out = rt.changed_pages(diff, "knowledge/", WATCH, IGNORE)
        self.assertEqual(out, [{"status": "added", "path": "customers/example.md"},
                               {"status": "modified", "path": "learnings/customer-value-patterns.md"}])

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
        diff = "M\tknowledge/analyses/enterprise-ideal-customer-profile.md\nM\tknowledge/contradictions.md\nM\tknowledge/customers/contradictions.md\nD\tknowledge/analyses/other.md\nM\tcontradictions.md"
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
            rt.write_tracks(tt, p)
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
