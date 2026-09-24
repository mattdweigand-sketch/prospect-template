"""Real deterministic preflight chains in isolated synthetic workspaces."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evidence_gate
import factory
import followup_gate
import outreach_gate
import route_candidate
import run_checks
import runs
from gate_fixtures import make_shared

NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def ready(path, effects=()):
    path.joinpath("01_review.md").write_text("---\nstatus: ready\nartifacts: []\n---\n# Synthetic review\n" +
                                            "".join("\n## Effect " + eid + "\nExact synthetic proposal.\n" for eid in effects))


def evidence(path, shared, now=NOW):
    signal = next(s for s in factory.taxonomy(shared)["signals"] if s["source"] == "web" and s["tier"] == 1)
    quote = "Example Account announced a new reporting initiative for its operations team."
    receipt = {"account_name": "Example Account", "account_aliases": ["Example Account"], "account_domain": "example.org",
               "source_url": "https://example.org/news", "published_date": now.date().isoformat(),
               "quote": quote, "evidence_subject": "Example Account", "signal_type": signal["id"], "quote_speaker": "account",
               "checked_at": (now - timedelta(minutes=5)).isoformat()}
    write(path / "receipt.json", receipt)
    (path / "source.txt").write_text(quote)
    code, result = evidence_gate.evaluate(receipt, quote, shared / "policy.json", now)
    assert code == 0, result
    write(path / "evidence.json", result)
    return {"receipt": "receipt.json", "page": "source.txt", "result": "evidence.json"}, result


def crm(policy, now=NOW):
    return {"account": {"id": "account-1", "name": "Example Account", "domain": "example.org",
                        "owner_id": policy["identity"]["owner_id"], "owner_is_active": True, "open_opportunity_ids": []},
            "tasks": [], "crm_complete": True, "tasks_complete": True,
            "activity_since": (now.date() - timedelta(days=max(policy["outreach"]["activity_lookback_days"], policy["scan"]["warm_engagement"]["lookback_days"]))).isoformat(),
            "read_reference": "synthetic-complete-crm"}


def claim_inputs(root, path, now=NOW):
    source, result = evidence(path, root / "_shared", now)
    bundle = result["bundle"]
    candidate = {"domain": "example.org", "headcount": 400,
                 "signals": [{"signal_type": bundle["signal_type"], "tier": bundle["tier"]}],
                 "account_exists": False, "owner_id": None, "owner_is_active": None, "open_opportunity_ids": [],
                 "vertical": "technology", "disqualifiers": []}
    write(path / "candidate.json", candidate)
    write(path / "routing.json", route_candidate.check(candidate, route_candidate.load_rules(root / "_shared")))
    write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "account_create", "input": "candidate.json"}}, "gaps": [],
                                 "sources": [source], "candidates": [{"receipt": "candidate.json", "result": "routing.json", "sources": ["evidence.json"]}]})
    ready(path, ["A1"])


def scan_run(root, name="scan", now=NOW):
    path = runs.init(root, name, "signal-scan")
    source, result = evidence(path, root / "_shared", now)
    write(path / "crm.json", crm(factory.read(root / "_shared/policy.json"), now))
    write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": [], "sources": [source], "crm": "crm.json"})
    ready(path)
    runs.record_review(root, name, "Synthetic reviewer", "synthetic-approval", [], now=now)
    return path, result


def handoff(root, source, dest, selected):
    review = factory.read(source / "review.json")
    export = review["validation"]["exports"][selected]
    target = dest / "handoff"
    target.mkdir()
    shutil.copyfile(source / "review.json", target / "review.json")
    mapping = {}
    for n, ref in enumerate(set(export["artifacts"]) | {selected}):
        copied = "handoff/" + str(n) + Path(ref).suffix
        shutil.copyfile(source / ref, dest / copied)
        mapping[ref] = copied
    return {"run_id": source.name, "workflow": review["validation"]["workflow"], "approval_reference": review["approval_reference"],
            "review": "handoff/review.json", "selected": selected, "artifacts": mapping}


def outreach_run(root, name="outreach", now=NOW):
    from test_outreach_gate import pk
    source, result = scan_run(root, name + "-scan", now)
    path = runs.init(root, name, "signal-outreach")
    packet = pk()
    packet["bundle"] = {**result["bundle"], "vertical": "technology"}
    packet["draft"]["body"] = "Hi Alex,\n\nYour reporting initiative suggests a workflow review. A review can establish which reports the team needs.\n\nWould a reporting review be useful?\n\nBest,\nSeller"
    write(path / "packet.json", packet)
    policy = factory.read(root / "_shared/policy.json")
    reasons = outreach_gate.check(packet, policy["outreach"], root / "_shared", now)
    assert not reasons, reasons
    out = {"verdict": "allow", "recipient": packet["recipient"]["email"], "signal_type": packet["bundle"]["signal_type"], "claim_id": packet["claim"]["id"],
           "flags": outreach_gate.fit_flags(packet, policy["outreach"], root / "_shared")}
    write(path / "gate.json", out)
    write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "draft", "input": "packet.json"}}, "gaps": [],
                                 "handoff": handoff(root, source, path, "evidence.json"), "packet": "packet.json", "result": "gate.json"})
    ready(path, ["A1"])
    return path, packet


class PreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "output", "__pycache__"))
        make_shared(self.root / "_shared")
        shutil.copyfile(self.root / "_shared/adapters.example.md", self.root / "_shared/adapters.md")

    def test_empty_artifact_outreach_cannot_record_review(self):
        path = runs.init(self.root, "empty", "signal-outreach")
        ready(path, ["A1"])
        write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "draft", "input": "packet.json"}}, "gaps": []})
        with self.assertRaisesRegex(ValueError, "preflight"):
            runs.record_review(self.root, path.name, "Synthetic", "test", ["A1"], now=NOW)

    def test_partial_scan_and_unknown_adoption_are_reviewable_without_handoff(self):
        for workflow in ("signal-scan", "signal-user-scan", "signal-arr-growth", "signal-followup"):
            with self.subTest(workflow=workflow):
                path = runs.init(self.root, workflow, workflow)
                ready(path)
                write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": ["Required provider unavailable."]})
                doc = runs.record_review(self.root, path.name, "Synthetic", "test", [], now=NOW)
                self.assertFalse(doc["validation"]["handoff_eligible"])
                self.assertTrue(doc["validation"]["issues"])

    def test_real_chain_and_saved_allow_replay(self):
        path, packet = outreach_run(self.root)
        doc = runs.record_review(self.root, path.name, "Synthetic", "test", ["A1"], now=NOW)
        self.assertEqual(runs.status(self.root, path.name)["state"], "review_current")
        self.assertTrue(doc["validation"]["handoff_eligible"])
        gate = factory.read(path / "gate.json")
        gate["claim_id"] = "fabricated"
        write(path / "gate.json", gate)
        self.assertEqual(runs.status(self.root, path.name)["state"], "review_stale")
        with self.assertRaisesRegex(ValueError, "preflight"):
            runs.record_review(self.root, path.name, "Synthetic", "test", ["A1"], now=NOW)

    def test_route_scoped_snapshot_and_frozen_time(self):
        path, _ = scan_run(self.root)
        (self.root / "_shared/claims.json").write_text("{}")
        self.assertEqual(runs.status(self.root, path.name)["state"], "review_current")
        with (self.root / "_shared/taxonomy.json").open("a") as out:
            out.write("\n")
        self.assertEqual(runs.status(self.root, path.name)["state"], "review_stale")

    def test_wrong_account_and_stale_source_handoff_block(self):
        path, packet = outreach_run(self.root)
        packet["bundle"]["account_domain"] = "different.example.org"
        write(path / "packet.json", packet)
        self.assertFalse(runs.preflight(self.root, path.name, now=NOW)["reviewable"])
        source = self.root / "output/outreach-scan/receipt.json"
        source.write_text(source.read_text() + "\n")
        self.assertIn("source review is stale", " ".join(runs.preflight(self.root, path.name, now=NOW)["issues"]))

    def test_scan_never_exports_another_crm_account(self):
        path = runs.init(self.root, "mismatch", "signal-scan")
        source, _ = evidence(path, self.root / "_shared")
        packet = crm(factory.read(self.root / "_shared/policy.json"))
        packet["account"]["domain"] = "another.example.org"
        write(path / "crm.json", packet)
        write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": ["Conflicting account identity."], "sources": [source], "crm": "crm.json"})
        ready(path)
        doc = runs.record_review(self.root, path.name, "Synthetic", "test", [], now=NOW)
        self.assertFalse(doc["validation"]["handoff_eligible"])

    def test_missing_naive_future_fetch_times_never_create_handoffs(self):
        for n, timestamp in enumerate((None, "2026-09-23T11:00:00", "2026-09-24T12:00:00+00:00")):
            path = runs.init(self.root, "bad-time-" + str(n), "signal-scan")
            source, _ = evidence(path, self.root / "_shared")
            receipt = factory.read(path / "receipt.json")
            receipt["checked_at"] = timestamp
            write(path / "receipt.json", receipt)
            write(path / "crm.json", crm(factory.read(self.root / "_shared/policy.json")))
            write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": ["Unusable source fetch time."], "sources": [source], "crm": "crm.json"})
            ready(path)
            doc = runs.record_review(self.root, path.name, "Synthetic", "test", [], now=NOW)
            self.assertFalse(doc["validation"]["handoff_eligible"])
            self.assertTrue(doc["validation"]["issues"])

    def test_mixed_candidates_keep_held_finding_without_blocking_valid_effect(self):
        path = runs.init(self.root, "mixed", "signal-prospector")
        claim_inputs(self.root, path)
        held = factory.read(path / "candidate.json")
        held["headcount"] = None
        write(path / "held.json", held)
        write(path / "held-result.json", route_candidate.check(held, route_candidate.load_rules(self.root / "_shared")))
        manifest = factory.read(path / "inputs.json")
        manifest["candidates"].append({"receipt": "held.json", "result": "held-result.json", "sources": ["evidence.json"]})
        write(path / "inputs.json", manifest)
        doc = runs.record_review(self.root, path.name, "Synthetic", "test", ["A1"], now=NOW)
        self.assertFalse(doc["validation"]["checks"]["candidate:2"]["claimable"])
        self.assertEqual(doc["validation"]["effects"]["A1"]["payload"]["owner_id"], "owner-1")

    def test_contact_dependency_requires_same_subject_and_approved_account(self):
        path = runs.init(self.root, "contact", "signal-prospector")
        claim_inputs(self.root, path)
        contact = {"first_name": "Alex", "last_name": "Example", "title": "Operations", "email": "alex@example.org",
                   "source": "verified enrichment", "source_reference": "synthetic-contact-read", "account_id": None}
        write(path / "contact.json", contact)
        manifest = factory.read(path / "inputs.json")
        manifest["effects"]["A2"] = {"kind": "contact_create", "input": "candidate.json", "account_effect": "A1"}
        manifest["candidates"][0]["contact"] = "contact.json"
        write(path / "inputs.json", manifest)
        ready(path, ["A1", "A2"])
        with self.assertRaisesRegex(ValueError, "requires its account"):
            runs.record_review(self.root, path.name, "Synthetic", "test", ["A2"], now=NOW)
        doc = runs.record_review(self.root, path.name, "Synthetic", "test", ["A1", "A2"], now=NOW)
        self.assertEqual(doc["validation"]["effects"]["A2"]["payload"]["account_effect"], "A1")

    def test_reviewed_aggregate_can_support_adoption_assisted_candidate(self):
        policy = factory.read(self.root / "_shared/policy.json")
        policy["adoption"]["enabled"] = True
        write(self.root / "_shared/policy.json", policy)
        aggregate = runs.init(self.root, "aggregate", "signal-user-scan")
        bundle = {"account_name": "Example Account", "account_id": "account-1", "account_domain": "example.org",
                  "data_through_date": "2026-09-22", "mapped_org_count": 0, "org_subscribed": False, "org_paying": False,
                  "org_service_types": [], "org_platforms": [], "paid_individuals_exist": True,
                  "adoption": "individuals_only", "source_reference": "synthetic-aggregate"}
        write(aggregate / "bundle.json", bundle)
        write(aggregate / "crm.json", crm(policy))
        write(aggregate / "receipt.json", {"success": True, "mapping_complete": True, "reference": "synthetic-aggregate", "checked_at": NOW.isoformat()})
        write(aggregate / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": [], "bundle": "bundle.json", "crm": "crm.json", "receipt": "receipt.json"})
        ready(aggregate)
        runs.record_review(self.root, aggregate.name, "Synthetic", "test", [], now=NOW)
        path = runs.init(self.root, "adoption-candidate", "signal-prospector")
        source, _ = evidence(path, self.root / "_shared")
        receipt = factory.read(path / "receipt.json")
        receipt["signal_type"] = "executive_statements"
        write(path / "receipt.json", receipt)
        _, qualified = evidence_gate.evaluate(receipt, (path / "source.txt").read_text(), self.root / "_shared/policy.json", NOW)
        write(path / "evidence.json", qualified)
        candidate = {"domain": "example.org", "headcount": 400, "account_id": "account-1", "account_exists": True, "owner_id": "owner-1", "owner_is_active": True,
                     "open_opportunity_ids": [], "vertical": "technology", "disqualifiers": [],
                     "signals": [{"signal_type": "executive_statements", "tier": "tier2"}, {"signal_type": "paid_individuals_present", "tier": "tier2"}]}
        write(path / "candidate.json", candidate)
        routing = route_candidate.check(candidate, route_candidate.load_rules(self.root / "_shared"))
        write(path / "routing.json", routing)
        write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": [], "sources": [source],
                                     "candidates": [{"receipt": "candidate.json", "result": "routing.json", "sources": ["evidence.json"],
                                                     "adoption": handoff(self.root, aggregate, path, "bundle.json")}]})
        ready(path)
        doc = runs.record_review(self.root, path.name, "Synthetic", "test", [], now=NOW)
        self.assertTrue(doc["validation"]["checks"]["candidate:1"]["admitted"])
        self.assertFalse(doc["validation"]["checks"]["candidate:1"]["claimable"])

    def test_setup_cannot_omit_changed_companion_file(self):
        from test_setup import SetupTests
        setup = SetupTests("test_product_and_service_businesses_install_their_own_mapping")
        setup.setUp()
        self.addCleanup(setup.doCleanups)
        path, post, source, _ = setup.configure()
        setup.review(path, post)
        review = path / "01_review.md"
        metadata = runs.review_metadata(path)
        del metadata["expected_after"]["A1"]["_shared/taxonomy.json"]
        review.write_text("---\nstatus: ready\nartifacts: " + json.dumps(metadata["artifacts"]) + "\nexpected_after: " + json.dumps(metadata["expected_after"]) + "\n---\n## Effect A1\nIncomplete installation.\n")
        report = runs.preflight(setup.root, path.name, source=Path(source["source"]), now=NOW)
        self.assertFalse(report["reviewable"])
        self.assertIn("omits changed companion", " ".join(report["issues"]))

    def arr_run(self):
        import arr_growth_gate
        from test_arr_growth_gate import row
        path = runs.init(self.root, "growth", "signal-arr-growth")
        packet = {"data_through_date": "2026-09-22", "rows": [row()], "immutable_input_reference": "snapshot:synthetic-v1"}
        result = arr_growth_gate.check(packet, factory.read(self.root / "_shared/policy.json"), NOW.date(), self.root / "_shared")
        draft = result["selected"][0]["draft"]
        write(path / "draft.json", draft)
        write(path / "selection.json", {"retention_authorized": True, "success": True, "reference": "synthetic-selection", "immutable_input_reference": "snapshot:synthetic-v1", "input_reference_kind": "immutable_snapshot"})
        write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "draft", "input": "draft.json"}}, "gaps": [], "drafts": [{"account_id": "account-1", "draft": "draft.json"}], "receipt": "selection.json"})
        ready(path, ["A1"])
        return path, packet

    def test_arr_only_safe_projection_is_retained_and_preimage_change_blocks(self):
        path, packet = self.arr_run()
        doc = runs.record_review(self.root, path.name, "Synthetic", "test", ["A1"], arr_packet=packet, now=NOW)
        encoded = json.dumps(doc)
        for secret in ("baseline_arr_usd", "current_arr_usd", "net_change_usd", "1200.0", "2400.0"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(doc["validation"]["checks"]["arr"]["financial_inputs"], "transient_not_replayable")
        changed = copy.deepcopy(packet)
        changed["rows"][0].update(current_arr_usd=2500.0, net_change_usd=1300.0)
        result = runs.preflight(self.root, path.name, arr_packet=changed, now=NOW)
        self.assertFalse(result["reviewable"])
        self.assertNotIn("2500", json.dumps(result))
        self.assertEqual(runs.status(self.root, path.name)["state"], "review_current")
        # A newly recorded actual approval may establish a fresh preimage; the
        # pre-effect command itself never does so.
        runs.record_review(self.root, path.name, "Synthetic", "new-test-approval", ["A1"], arr_packet=changed, now=NOW)
        self.assertTrue(runs.preflight(self.root, path.name, arr_packet=changed, now=NOW)["reviewable"])

    def test_arr_cli_is_private_and_rejects_query_id_only_receipts(self):
        path, packet = self.arr_run()
        result = subprocess.run([sys.executable, "-B", "scripts/runs.py", "preflight", path.name, "--arr-packet", "-", "--now", NOW.isoformat()],
                                cwd=self.root, input=json.dumps(packet), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("baseline_arr_usd", result.stdout + result.stderr)
        receipt = factory.read(path / "selection.json")
        receipt["input_reference_kind"] = "query_execution"
        write(path / "selection.json", receipt)
        self.assertFalse(runs.preflight(self.root, path.name, arr_packet=packet, now=NOW)["reviewable"])
        malformed = subprocess.run([sys.executable, "-B", "scripts/runs.py", "preflight", path.name, "--arr-packet", "-"],
                                   cwd=self.root, input='{"private_amount": 987654 broken', capture_output=True, text=True)
        self.assertEqual(malformed.returncode, 2)
        self.assertEqual(json.loads(malformed.stdout)["verdict"], "error")
        self.assertNotIn("987654", malformed.stdout + malformed.stderr)

    def test_malformed_manifest_reports_json_and_legacy_review_is_not_actionable(self):
        path = runs.init(self.root, "malformed", "signal-scan")
        ready(path)
        (path / "inputs.json").write_text("[]")
        result = subprocess.run([sys.executable, "-B", "scripts/runs.py", "preflight", path.name], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["verdict"], "error")
        write(path / "review.json", {"reviewer": "Old reviewer", "approval_reference": "old", "snapshot": {}})
        self.assertEqual(runs.status(self.root, path.name)["state"], "review_stale")

    def test_gap_explanations_do_not_hide_malformed_manifest_structures(self):
        malformed = [("signal-scan", {"sources": [{}]}),
                     ("signal-scan", {"sources": "missing"}),
                     ("signal-prospector", {"candidates": [{"receipt": "candidate.json"}]}),
                     ("signal-outreach", {"handoff": {}}),
                     ("signal-followup", {"mode": "invented"}),
                     ("signal-arr-growth", {"drafts": [{}]}),
                     ("signal-refresh", {"diagnostic": {}})]
        for n, (workflow, fields) in enumerate(malformed):
            with self.subTest(workflow=workflow, fields=fields):
                path = runs.init(self.root, "malformed-" + str(n), workflow)
                ready(path)
                write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": ["Provider unavailable."], **fields})
                with self.assertRaises(ValueError):
                    runs.record_review(self.root, path.name, "Synthetic", "test", [], now=NOW)
                result = subprocess.run([sys.executable, "-B", "scripts/runs.py", "preflight", path.name], cwd=self.root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["verdict"], "error")

    def test_portable_standard_and_arr_handoffs_preserve_followup_account(self):
        for mode in ("standard", "arr_growth"):
            with self.subTest(mode=mode):
                if mode == "standard":
                    source, packet = outreach_run(self.root, "portable-outreach")
                    runs.record_review(self.root, source.name, "Synthetic", "test", ["A1"], now=NOW)
                    selected = "packet.json"
                    email = {"to": packet["recipient"]["email"], **packet["draft"]}
                    signal = {"signal_type": packet["bundle"]["signal_type"], "claim_id": packet["claim"]["id"]}
                else:
                    source, packet = self.arr_run()
                    runs.record_review(self.root, source.name, "Synthetic", "test", ["A1"], arr_packet=packet, now=NOW)
                    selected = "draft.json"
                    email = factory.read(source / selected)
                    signal = {"signal_type": "arr_growth", "claim_id": "arr_growth"}
                path = runs.init(self.root, "portable-followup-" + mode.replace("_", "-"), "signal-followup")
                fp = {"sent": [{"message_id": "message-1", "thread_id": "thread-1", "subject": email["subject"], "sent_at": NOW.isoformat(), "to": email["to"]}],
                      "sent_lookup_reference": "live-synthetic-send", "account": {"id": "account-1", "owner_id": "owner-1", "open_opportunity_ids": []},
                      "contacts": [{"id": "contact-1", "account_id": "account-1", "email": email["to"]}], "contacts_complete": True,
                      "tasks": [], "tasks_complete": True, "signal": signal}
                write(path / "packet.json", fp)
                policy = factory.read(self.root / "_shared/policy.json")
                write(path / "gate.json", followup_gate.check(fp, mode, policy, NOW, self.root / "_shared"))
                write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "task", "input": "packet.json"}}, "gaps": [], "mode": mode,
                                            "packet": "packet.json", "result": "gate.json", "handoff": handoff(self.root, source, path, selected)})
                ready(path, ["A1"])
                # The copied review and selected artifacts must suffice after
                # transfer to a host where the original source run is absent.
                shutil.rmtree(source)
                self.assertTrue(runs.preflight(self.root, path.name, now=NOW)["reviewable"])
                fp["account"]["id"] = "entirely-other-account"
                fp["contacts"][0]["account_id"] = "entirely-other-account"
                write(path / "packet.json", fp)
                standalone = followup_gate.check(fp, mode, policy, NOW, self.root / "_shared")
                self.assertEqual(standalone["verdict"], "allow")
                write(path / "gate.json", standalone)
                result = runs.preflight(self.root, path.name, now=NOW)
                self.assertFalse(result["reviewable"])
                self.assertIn("account differs", " ".join(result["issues"]))

    def test_internal_adoption_domains_and_mismatched_receipt_never_export(self):
        policy = factory.read(self.root / "_shared/policy.json")
        policy["adoption"]["enabled"] = True
        write(self.root / "_shared/policy.json", policy)
        for n, domain in enumerate(("example.com", "EXAMPLE.COM.", "team.example.com", "example.org")):
            path = runs.init(self.root, "adoption-boundary-" + str(n), "signal-user-scan")
            bundle = {"account_name": "Example Account", "account_id": "account-1", "account_domain": domain,
                      "data_through_date": "2026-09-22", "mapped_org_count": 0, "org_subscribed": False, "org_paying": False,
                      "org_service_types": [], "org_platforms": [], "paid_individuals_exist": True,
                      "adoption": "individuals_only", "source_reference": "synthetic-aggregate"}
            account = crm(policy)
            account["account"]["domain"] = domain
            write(path / "bundle.json", bundle)
            write(path / "crm.json", account)
            write(path / "receipt.json", {"success": True, "mapping_complete": True, "reference": "different-aggregate" if n == 3 else "synthetic-aggregate", "checked_at": NOW.isoformat()})
            write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": ["Held domain or receipt mismatch."], "bundle": "bundle.json", "crm": "crm.json", "receipt": "receipt.json"})
            ready(path)
            doc = runs.record_review(self.root, path.name, "Synthetic", "test", [], now=NOW)
            self.assertFalse(doc["validation"]["handoff_eligible"])
            self.assertTrue(doc["validation"]["issues"])

    def test_real_refetch_and_later_followup_do_not_rewrite_history(self):
        path, packet = outreach_run(self.root)
        later = NOW + timedelta(days=2)
        receipt = factory.read(self.root / "output/outreach-scan/receipt.json")
        receipt["checked_at"] = later.isoformat()
        write(path / "fresh-receipt.json", receipt)
        (path / "fresh-page.txt").write_text(receipt["quote"] + "\nNew harmless page footer.")
        _, result = evidence_gate.evaluate(receipt, (path / "fresh-page.txt").read_text(), self.root / "_shared/policy.json", later)
        write(path / "fresh-result.json", result)
        packet["bundle"] = {**result["bundle"], "vertical": "technology"}
        write(path / "packet.json", packet)
        manifest = factory.read(path / "inputs.json")
        manifest["refreshed"] = {"receipt": "fresh-receipt.json", "page": "fresh-page.txt", "result": "fresh-result.json"}
        write(path / "inputs.json", manifest)
        runs.record_review(self.root, path.name, "Synthetic", "test", ["A1"], now=later)
        follow = runs.init(self.root, "followup", "signal-followup")
        sent_time = later + timedelta(days=3)
        fp = {"sent": [{"message_id": "message-1", "thread_id": "thread-1", "subject": packet["draft"]["subject"], "sent_at": sent_time.isoformat(), "to": packet["recipient"]["email"]}],
              "sent_lookup_reference": "live-synthetic-send", "account": {"id": "account-1", "owner_id": "owner-1", "open_opportunity_ids": []},
              "contacts": [{"id": "contact-1", "account_id": "account-1", "email": packet["recipient"]["email"]}], "contacts_complete": True,
              "tasks": [], "tasks_complete": True, "signal": {"signal_type": packet["bundle"]["signal_type"], "claim_id": packet["claim"]["id"]}}
        write(follow / "packet.json", fp)
        write(follow / "gate.json", followup_gate.check(fp, "standard", factory.read(self.root / "_shared/policy.json"), sent_time, self.root / "_shared"))
        write(follow / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "task", "input": "packet.json"}}, "gaps": [], "mode": "standard",
                                        "packet": "packet.json", "result": "gate.json", "handoff": handoff(self.root, path, follow, "packet.json")})
        ready(follow, ["A1"])
        runs.record_review(self.root, follow.name, "Synthetic", "test", ["A1"], now=sent_time)


if __name__ == "__main__":
    unittest.main()
