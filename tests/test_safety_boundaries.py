"""Regressions for evidence, approval, privacy and private adapter boundaries."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from gate_fixtures import ROOT, SCRIPTS, SHARED, make_shared
import approval
import arr_growth_gate
import build_pairings
import evidence_gate
import factory
import followup_gate
import lint_draft
import outreach_gate
import privacy_check
import refresh_tracks
import route_candidate
import test_arr_growth_gate as growth
import test_evidence_gate as evidence
import test_followup_gate as followup
import test_outreach_gate as outreach
import test_privacy_check as privacy
import test_route_candidate as routing


class SafetyBoundaries(unittest.TestCase):
    def test_frontmatter_delimiters_inside_json_and_prose(self):
        with tempfile.TemporaryDirectory() as directory:
            shared = make_shared(directory)
            fm = factory.frontmatter(shared)
            fm["persona_cares"]["champion"] = "Uses --- as an explicit separator."
            body = "# Synthetic body\n\n---\n\nKeep this unchanged.\n"
            (shared / "icp.md").write_text("---\n" + json.dumps(fm) + "\n---\n" + body)
            self.assertEqual(factory.frontmatter(shared), fm)
            factory.write_frontmatter(shared, fm)
            self.assertTrue((shared / "icp.md").read_text().endswith(body))

    def test_outreach_dates_use_configured_timezone(self):
        now = datetime(2026, 9, 23, 1, tzinfo=timezone.utc)  # Still Sep 22 in configured Pacific time.
        packet = outreach.pk(bundle__published_date="2026-09-23")
        self.assertIn("bundle published_date is in the future", outreach_gate.check(packet, outreach.POL, SHARED, now))

    def test_duplicate_tier2_does_not_admit(self):
        self.assertFalse(route_candidate.check(routing.receipt(signals=routing.T2 * 2), routing.RULES)["admitted"])

    def test_inactive_and_house_owners_never_bypass_open_deal(self):
        for owner, active in (("inactive-owner", False), ("house-1", True)):
            out = route_candidate.check(routing.receipt(account_exists=True, owner_id=owner, owner_is_active=active,
                                                      open_opportunity_ids=["deal-1"]), routing.RULES)
            self.assertEqual(out["route"], "active_deal")
            self.assertFalse(out["claimable"])

    def test_internal_domain_and_subdomain_cannot_be_claimed(self):
        for domain in ("example.com", "team.example.com"):
            self.assertEqual(route_candidate.check(routing.receipt(domain=domain), routing.RULES)["route"], "internal_domain")

    def test_signal_tier_cannot_be_overstated(self):
        with self.assertRaises(ValueError):
            route_candidate.check(routing.receipt(signals=[{"signal_type": "exec_ai_statements", "tier": "tier1"}]), routing.RULES)

    def test_adoption_needs_owned_account_and_web_tier2(self):
        signals = [{"signal_type": "paid_individuals_present", "tier": "tier2"}] + routing.T2
        self.assertFalse(route_candidate.check(routing.receipt(signals=signals), routing.RULES)["admitted"])
        out = route_candidate.check(routing.receipt(signals=signals, account_exists=True, owner_id="owner-1", owner_is_active=True), routing.RULES)
        self.assertTrue(out["admitted"])
        self.assertEqual(out["route"], "scan")
        self.assertFalse(out["claimable"])
        no_web = [signals[0]] + routing.T1
        self.assertFalse(route_candidate.check(routing.receipt(signals=no_web, account_exists=True, owner_id="owner-1", owner_is_active=True), routing.RULES)["admitted"])

    def test_invalid_headcount_cannot_enter_territory(self):
        for value in (True, -1, "1200", 1000.5):
            with self.assertRaises(ValueError):
                route_candidate.check(routing.receipt(headcount=value), routing.RULES)

    def test_event_fallback_requires_first_party(self):
        pol, types = evidence_gate.load_taxonomy(SHARED / "policy.json")
        code, out = evidence_gate.grade(evidence.receipt(published_date=None, event_date="2026-09-01", quote_speaker="third_party"),
                                        evidence.PAGE + " 2026-09-01", pol, types, evidence.TODAY)
        self.assertEqual((code, out["reason"]), (1, "event_fallback_requires_first_party"))
        code, out = evidence_gate.grade(evidence.receipt(published_date=None, event_date="2026-09-01", source_url="https://example.net/article"),
                                        evidence.PAGE + " 2026-09-01", pol, types, evidence.TODAY)
        self.assertEqual((code, out["reason"]), (1, "event_fallback_requires_account_host"))

    def test_saved_page_recheck_preserves_fetch_time(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            (d / "receipt.json").write_text(json.dumps(evidence.receipt()))
            (d / "page.txt").write_text(evidence.PAGE)
            cmd = [sys.executable, "-B", str(SCRIPTS / "evidence_gate.py"), "--receipt", str(d / "receipt.json"),
                   "--page", str(d / "page.txt"), "--policy", str(SHARED / "policy.json"), "--now", "2026-09-21T12:00:00-07:00"]
            missing = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(missing.returncode, 2)
            fetched = "2026-09-20T01:02:03+00:00"
            result = subprocess.run(cmd + ["--checked-at", fetched], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout)["bundle"]["checked_at"], fetched)

    def test_future_outreach_dates_block(self):
        for key, value in (("published_date", "2027-01-01"), ("checked_at", (outreach.NOW + timedelta(minutes=1)).isoformat())):
            packet = outreach.pk(**{"bundle__" + key: value})
            self.assertTrue(any("future" in r for r in outreach_gate.check(packet, outreach.POL, SHARED, outreach.NOW)))

    def test_outreach_requires_activity_and_voice_receipts(self):
        for key in ("activity_complete", "voice_anchor_reference"):
            p = outreach.pk()
            p.pop(key)
            self.assertTrue(outreach_gate.check(p, outreach.POL, SHARED, outreach.NOW))
        p = outreach.pk()
        p["activity"].append({"kind": "unknown_provider_event", "date": "2026-09-22"})
        with self.assertRaises(ValueError):
            outreach_gate.check(p, outreach.POL, SHARED, outreach.NOW)

    def test_fit_mode_block_holds_matrix_gap(self):
        p = outreach.row_packet("api_embed", "ai_exec_appointment", vertical="legal", persona="technical_evaluator", title="CIO")
        self.assertFalse(outreach_gate.check(p, outreach.POL, SHARED, outreach.NOW))
        self.assertTrue(outreach_gate.check(p, {**outreach.POL, "fit_mode": "block"}, SHARED, outreach.NOW))

    def test_unapproved_status_blocks_even_current_hash(self):
        with tempfile.TemporaryDirectory() as d:
            shared = make_shared(d)
            doc = factory.claim_document(shared)
            doc["claims"][0]["status"] = "example"
            doc["claims"][0]["approved"] = approval.make_stamp(doc["claims"][0], "2026-09-22")
            factory.write(shared / "claims.json", doc)
            self.assertIn("claim status is not approved", outreach_gate.check(outreach.pk(), outreach.POL, shared, outreach.NOW))

    def test_adoption_statement_requires_date_account_review_and_enablement(self):
        with tempfile.TemporaryDirectory() as d:
            shared = make_shared(d)
            pol = factory.read(shared / "policy.json")
            sentence = "An organization subscription is mapped to this account."
            pol["adoption"].update(enabled=True, approved_statements={"org_adopted": sentence})
            factory.write(shared / "policy.json", pol)
            p = outreach.pk()
            p.update(adoption_sentence=sentence, adoption_bundle={**privacy.CLEAN, "data_through_date": "2026-09-21"},
                     adoption_review_reference="synthetic-review", adoption_checked_at=outreach.NOW.isoformat())
            p["draft"]["body"] += "\n\n" + sentence
            self.assertEqual(outreach_gate.check(p, outreach.POL, shared, outreach.NOW), [])
            for field, value in (("data_through_date", "2026-09-20"), ("account_domain", "example.net")):
                bad = copy.deepcopy(p)
                bad["adoption_bundle"][field] = value
                self.assertTrue(outreach_gate.check(bad, outreach.POL, shared, outreach.NOW))
            p["adoption_review_reference"] = ""
            self.assertTrue(outreach_gate.check(p, outreach.POL, shared, outreach.NOW))
            pol["adoption"]["enabled"] = False
            factory.write(shared / "policy.json", pol)
            self.assertIn("adoption adapter disabled", outreach_gate.check(p, outreach.POL, shared, outreach.NOW))

    def test_privacy_rejects_nested_values_and_inconsistent_categories(self):
        allowed = privacy_check.load_policy(SHARED / "policy.json")
        for changes in ({"org_platforms": [{"person": "hidden"}]}, {"adoption": "none_found"},
                        {"data_through_date": "yesterday"}, {"mapped_org_count": -1}):
            self.assertTrue(privacy_check.check({**privacy.CLEAN, **changes}, allowed))

    def test_growth_requires_enabled_current_completed_data(self):
        for enabled, through in ((False, "2026-09-20"), (True, "2026-09-19")):
            pol = copy.deepcopy(growth.POLICY)
            pol["arr_growth"]["enabled"] = enabled
            out = arr_growth_gate.check({"data_through_date": through, "rows": [growth.row()]}, pol, growth.TODAY, SHARED)
            self.assertEqual(out["verdict"], "block")

    def test_growth_rejects_nonfinite_and_inconsistent_amounts(self):
        for change in (float("nan"), float("inf"), True):
            row = growth.row()
            row["net_change_usd"] = change
            self.assertEqual(growth.run(row)["held"][0]["hold"], "invalid_arr_values")
        row = growth.row()
        row["current_arr_usd"] += 10
        self.assertEqual(growth.run(row)["held"][0]["hold"], "inconsistent_arr_values")

    def test_growth_requires_coverage_mapping_and_live_read_proofs(self):
        for field in ("daily_coverage_verified", "mapping_verified", "activity_complete", "contacts_complete"):
            row = growth.row()
            row.pop(field)
            self.assertEqual(growth.run(row)["verdict"], "block")
        row = growth.row()
        row["account"].pop("open_opportunity_ids")
        self.assertEqual(growth.run(row)["held"][0]["hold"], "incomplete_live_reads")

    def test_growth_holds_all_ambiguous_mappings(self):
        out = growth.run(growth.row(), growth.row())
        self.assertEqual(out["selected"], [])
        self.assertEqual({r["hold"] for r in out["held"]}, {"duplicate_account_mapping"})

    def test_growth_rejects_unsorted_rows(self):
        with self.assertRaises(ValueError):
            growth.run(growth.row(account_id="account-2", net_change_usd=50), growth.row())

    def test_growth_stdin_has_same_result_without_input_file(self):
        packet = {"data_through_date": "2026-09-20", "rows": [growth.row()]}
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "arr_growth_gate.py"), "--packet", "-",
                                 "--shared", str(SHARED), "--today", "2026-09-21"],
                                input=json.dumps(packet), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout), growth.run(growth.row()))

    def test_followup_requires_complete_proof_and_contact_association(self):
        for key in ("tasks_complete", "contacts_complete", "sent_lookup_reference"):
            packet = copy.deepcopy(followup.BASE)
            packet.pop(key)
            self.assertEqual(followup_gate.check(packet, "standard", followup.POLICY, followup.NOW, SHARED)["verdict"], "block")
        packet = copy.deepcopy(followup.BASE)
        packet["contacts"][0]["account_id"] = "different-account"
        self.assertEqual(followup_gate.check(packet, "standard", followup.POLICY, followup.NOW, SHARED)["verdict"], "block")

    def test_followup_future_send_and_invalid_cadence_block(self):
        self.assertEqual(followup.run(sent=[{**followup.BASE["sent"][0], "sent_at": "2027-01-01T01:00:00Z"}])["verdict"], "block")
        for value in (-1, True, 1.5):
            pol = copy.deepcopy(followup.POLICY)
            pol["followup_signal"]["growth_due_business_days"] = value
            with self.assertRaises(ValueError):
                followup_gate.due_date("2026-09-21T10:00:00Z", "arr_growth", pol)

    def test_email_lint_checks_phrases_punctuation_and_format(self):
        rules = outreach.POL["lint"]
        self.assertEqual(lint_draft.check("Hi reader,\n\nWould a reporting review help?", rules), [])
        for body in ("Excited to share this", "This — that", "#update", "**Update**", "- detail", "1. detail", "# Title", "Hello 😀"):
            with self.subTest(body=body): self.assertTrue(lint_draft.check(body, rules))
        self.assertEqual(lint_draft.check("word " * 90, rules), [])
        self.assertTrue(lint_draft.check("word " * 91, rules))
        self.assertEqual(lint_draft.check("Which shared spaces need a reporting review?", rules), [])


class PinnedRefresh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.shared = make_shared(self.root / "shared")
        self.wiki = self.root / "wiki"
        (self.wiki / "products").mkdir(parents=True)
        self.page = self.wiki / "products/example.md"
        self.source = "\n".join(row["evidence"] for row in factory.claim_document(self.shared)["claims"])
        self.page.write_text(self.source)
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "synthetic source")

    def git(self, *args):
        return refresh_tracks.git(self.wiki, *args)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / "refresh_tracks.py"), "--wiki", str(self.wiki),
                               "--shared", str(self.shared), *map(str, args)], capture_output=True, text=True)

    def test_report_reads_commit_not_dirty_working_tree(self):
        self.page.write_text("Changed locally; no supporting evidence.")
        self.assertEqual(refresh_tracks.report(self.wiki, self.shared)["broken_rows"], [])
        self.git("add", ".")
        self.git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "remove evidence")
        self.page.write_text(self.source)
        self.assertEqual(len(refresh_tracks.report(self.wiki, self.shared)["broken_rows"]), 9)

    def test_cli_stamps_only_staged_postimages(self):
        before = {p.name: p.read_bytes() for p in self.shared.iterdir()}
        denied = self.cli("--stamp")
        self.assertEqual(denied.returncode, 2)
        stage = self.root / "postimages"
        result = self.cli("--stamp", "--approve-rows", "completed_work", "--stage", stage)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.shared.iterdir()})
        self.assertEqual(factory.claim_document(stage)["source_revision"], self.git("rev-parse", "HEAD"))
        self.assertEqual(json.loads(result.stdout)["stage_status"], "proposed_only_requires_exact_review")
        for row in factory.claim_document(stage)["claims"]:
            if row["id"] != "completed_work":
                original = next(r for r in factory.claim_document(self.shared)["claims"] if r["id"] == row["id"])
                self.assertEqual(row["approved"], original["approved"])

    def test_unknown_unit_and_active_subdirectory_rejected_before_writes(self):
        stage = self.root / "invalid"
        self.assertEqual(self.cli("--approve-rows", "all", "--stage", stage).returncode, 2)
        self.assertFalse(stage.exists())
        self.assertEqual(self.cli("--stage", self.shared / "nested").returncode, 2)
        self.assertFalse((self.shared / "nested").exists())

    def test_committed_symlink_and_traversal_are_rejected(self):
        self.page.unlink()
        self.page.symlink_to("../unread-secret.md")
        self.git("add", ".")
        self.git("-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.com", "commit", "-qm", "symlink")
        with self.assertRaises(ValueError): refresh_tracks.report(self.wiki, self.shared)
        with self.assertRaises(ValueError): refresh_tracks.source_path("", "../outside")

    def test_missing_watch_page_prevents_source_stamp(self):
        pol = factory.read(self.shared / "policy.json")
        pol["refresh"]["watch_paths"] = ["missing-policy.md"]
        factory.write(self.shared / "policy.json", pol)
        rep = refresh_tracks.report(self.wiki, self.shared)
        self.assertEqual(rep["missing_watch_pages"], ["missing-policy.md"])
        self.assertEqual(self.cli("--stamp", "--stage", self.root / "bad").returncode, 2)

    def test_deleted_watch_file_is_reported(self):
        self.assertEqual(refresh_tracks.changed_watch_files("D\twiki/personas.md", "wiki", ["personas.md"]), ["personas.md"])

    def test_pairings_reject_unknown_and_unreachable_claims(self):
        _, errors = build_pairings.build(self.shared)
        self.assertEqual(errors, [])
        tax = factory.read(self.shared / "taxonomy.json")
        for signal in tax["signals"]:
            signal["claim_ids"] = [rid for rid in signal["claim_ids"] if rid != "api_embed"]
        tax["signals"][0]["claim_ids"].append("missing-row")
        factory.write(self.shared / "taxonomy.json", tax)
        _, errors = build_pairings.build(self.shared)
        self.assertIn("unreachable claim: api_embed", errors)
        self.assertIn("unknown claim: missing-row", errors)

    def test_examples_remain_unapproved_and_private_capabilities_disabled(self):
        pol = json.loads((ROOT / "_shared/policy.example.json").read_text())
        self.assertEqual(pol["mode"], "example")
        self.assertFalse(pol["adoption"]["enabled"])
        self.assertFalse(pol["arr_growth"]["enabled"])
        self.assertIsNone(pol["arr_growth"]["email_template"])
        for row in json.loads((ROOT / "_shared/claims.example.json").read_text())["claims"]:
            self.assertNotEqual(row["status"], "approved")
            self.assertFalse(approval.stamp_current(row, row["approved"]))


if __name__ == "__main__":
    unittest.main()
