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
            (Path(d) / "learnings" / "a.md").write_text("Intro.\nComputer  hands back\nfinished Work.\n")
            rows = [{"id": "ok", "source_reference": "learnings/a.md", "evidence": "computer hands back finished work."},
                    {"id": "bad", "source_reference": "learnings/a.md", "evidence": "Computer drafts work."},
                    {"id": "gone", "source_reference": "learnings/b.md", "evidence": "x"}]
            broken, missing = rt.verify_rows(rows, d)
            self.assertEqual([b["id"] for b in broken], ["bad"])
            self.assertEqual([m["id"] for m in missing], ["gone"])

    def test_changed_pages_filters_dirs_ignores_and_deletes(self):
        diff = "A\twiki/customers/example.md\nM\twiki/index.md\nM\twiki/systems/x.md\nD\twiki/learnings/old.md\nM\twiki/learnings/customer-value-patterns.md\nR100\twiki/customers/a.md\twiki/customers/b.md\nM\tREADME.md"
        out = rt.changed_pages(diff, "wiki/", WATCH, IGNORE)
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
        diff = "M\twiki/analyses/enterprise-ideal-customer-profile.md\nM\twiki/contradictions.md\nM\twiki/customers/contradictions.md\nD\twiki/analyses/other.md\nM\tcontradictions.md"
        out = rt.changed_watch_files(diff, "wiki/", ["analyses/enterprise-ideal-customer-profile.md", "contradictions.md"])
        self.assertEqual(out, ["analyses/enterprise-ideal-customer-profile.md", "contradictions.md"])

    def test_contradiction_flags_match_open_entries_only(self):
        text = ("# Contradictions\n\n## Open\n\n### [Status: open] Sandbox API availability\n"
                "Claim A: x - source: [[example-api]]\nClaim B: y - source: [[sandbox-page|Sandbox]]\n\n"
                "## Resolved\n\n### [Status: resolved] Old one\nClaim A: z - source: [[customer-value-patterns]]\n")
        rows = [{"id": "agent_api", "source_reference": "products/example-api.md"},
                {"id": "completed_work", "source_reference": "learnings/customer-value-patterns.md"},
                {"id": "hybrid_local", "source_reference": "sources/sandbox-page.md"}]
        out = rt.contradiction_flags(text, rows)
        self.assertEqual(sorted(o["id"] for o in out), ["agent_api", "hybrid_local"])
        self.assertEqual(out[0]["contradiction"], "Sandbox API availability")

    def test_approve_rows_restamps_only_named_rows(self):
        import shutil
        import approval
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(SHARED / "claims.json", Path(d) / "claims.json")
            p = Path(d) / "claims.json"
            tt = json.loads(p.read_text())
            for r in tt["claims"]:
                if r["id"] in ("completed_work", "domain_context"):
                    r["track"] = "Changed."
            rt.write_tracks(tt, p)
            tt = json.loads(p.read_text())
            stale = [r["id"] for r in tt["claims"] if not approval.stamp_current(r, r.get("approved"))]
            self.assertEqual(stale, ["completed_work", "domain_context"])
            done = rt.approve_rows({"completed_work"}, Path(d), today="2026-10-02")
            self.assertEqual(done, ["completed_work"])
            tt = json.loads(p.read_text())
            stale = [r["id"] for r in tt["claims"] if not approval.stamp_current(r, r.get("approved"))]
            self.assertEqual(stale, ["domain_context"])
            cw = next(r for r in tt["claims"] if r["id"] == "completed_work")
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
