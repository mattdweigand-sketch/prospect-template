"""Product/service setup and update rehearsals. All sources and approvals are synthetic.

Tests verify configuration, evidence and review mechanics. Sample selections are
explicit fixtures, not proof of an agent's semantic ranking or email quality.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_repo
import factory
import source_snapshot
import validate_setup

NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="prospect-setup-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for ref in check_repo.public_files(ROOT):
            target = self.root / ref
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / ref, target)
        self.public = {str(p): digest(self.root / p) for p in check_repo.public_files(self.root)}
        self.shared = self.root / "_shared"
        for example in self.shared.glob("*.example.*"):
            shutil.copyfile(example, example.with_name(example.name.replace(".example", "")))

    def cli(self, script, *args, code=0):
        result = subprocess.run([sys.executable, "-B", "scripts/" + script + ".py", *map(str, args)],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        try:
            return json.loads(result.stdout)
        except ValueError:
            return result.stdout

    def configure(self, business="research"):
        self.cli("runs", "init", business, "prospect-setup")
        run = self.root / "output" / business
        proposal = run / "proposal"
        proposal.mkdir()
        for example in self.shared.glob("*.example.*"):
            shutil.copyfile(example, proposal / example.name.replace(".example", ""))
        if business == "research":
            company, vertical, persona, title = "Scout Example", "services", "market_owner", "Research"
            evidence = "Scout Example lets researchers compare information from published market reports in a single view."
            track = "Scout Example compares published market information."
            work = "Compare market information before selecting an expansion market."
            quote = "Example Account plans to compare market reports before choosing its next expansion market."
        elif business == "localization":
            company, vertical, persona, title = "Locale Example", "retail", "content_owner", "Localization"
            evidence = "Locale Example provides a review queue where editors can approve translated product content."
            track = "Locale Example routes translated content for approval."
            work = "Prepare and review translated product content for a new market."
            quote = "Example Account plans to review translated product content before entering its next market."
        else:
            company, vertical, persona, title = "Clean Example", "property_management", "facilities_owner", "Facilities Manager"
            evidence = "Clean Example provides commercial cleaning crews for newly opened office facilities."
            track = "Clean Example offers cleaning for new offices."
            work = "Arrange cleaning coverage before opening new offices."
            quote = "Example Account plans to establish cleaning coverage before opening its new office."
        signal_id = "facility_opening" if business == "cleaning" else "market_entry"
        other_id = "site_inspection" if business == "cleaning" else "access_review"
        policy = factory.read(proposal / "policy.json")
        policy["identity"]["owner_id"] = business + "-owner"
        policy["outreach"].update(suppression_days=45, activity_lookback_days=45)
        policy["outreach"]["task_status_map"] = {"Done": "completed", "Queued": "open", "Cancelled": "cancelled"}
        policy["followup_signal"]["due_calendar_days"] = 12
        policy["email_voice"]["anchor_reference"] = "supplied:synthetic-voice"
        policy["refresh"]["source"] = str(run / "source")
        factory.write(proposal / "policy.json", policy)
        icp = factory.frontmatter(proposal)
        icp.update(status="configured", verticals=[{"id": vertical, "rank": 1}],
                   territory={"min_employees": 50 if business == "research" else 200, "max_employees": 2000},
                   persona_cares={persona: work})
        factory.write_frontmatter(proposal, icp)
        doc = factory.read(proposal / "claims.json")
        row = doc["claims"][0]
        row.update(id=business + "_value", status="approved", claim=track, track=track, evidence=evidence,
                   limit="Offer capability only; no guaranteed business result or customer proof.",
                   source_reference="materials/product.txt", verticals=[vertical], personas=[persona],
                   approval_reference="output/" + business + "/01_review.md (proposed synthetic review)")
        other = copy.deepcopy(row)
        other.update(id="access_review", claim=company + " supports reviewing administrator access.",
                     track=company + " supports reviewing administrator access.",
                     evidence=company + " displays assigned administrator roles for review by an account owner.")
        if business == "cleaning":
            other.update(id=other_id, claim="Clean Example offers site inspections.", track="Clean Example offers site inspections.",
                         evidence="Clean Example performs a site inspection before proposing a commercial cleaning schedule.")
        doc["claims"].append(other)
        factory.write(proposal / "claims.json", doc)
        signal = factory.read(proposal / "taxonomy.json")["signals"][0]
        signal.update(id=signal_id, definition="An account plans a new office opening." if business == "cleaning" else "An account plans entry into a new market.",
                      creates_work=work, target_titles=[title], claim_ids=[row["id"]], example_queries=["company market expansion"])
        if business == "cleaning":
            signal["example_queries"] = ["company new office opening"]
        second = copy.deepcopy(signal)
        second.update(id=other_id, tier=2, definition="An account is reviewing administrator access.",
                      creates_work="Review administrator access.", claim_ids=[other["id"]])
        if business == "cleaning":
            second.update(definition="An account seeks an inspection of its site.", creates_work="Inspect the site before selecting cleaning services.")
        factory.write(proposal / "taxonomy.json", {"signals": [signal, second]})
        (run / "product.txt").write_text(evidence + "\n" + other["evidence"] + "\n")
        (run / "voice.txt").write_text("Hi Alex,\n\nYour plan suggests a workflow review. Would that be useful?\n\nBest,\nSeller")
        factory.write(run / "intake.json", {"sources": [{"path": "product.txt", "reference": "materials/product.txt",
                                                       "origin": "Fictional supplied product guide", "kind": "source"}]})
        source = self.cli("source_snapshot", "--manifest", run / "intake.json", "--destination", run / "source")
        before = {name: digest(self.shared / name) for name in ("policy.json", "claims.json", "taxonomy.json", "icp.md")}
        post = run / "postimages"
        self.cli("refresh_tracks", "--source", source["source"], "--revision", source["revision"], "--shared", proposal,
                 "--stage", post, "--approve-rows", row["id"] + "," + other_id, "--approve-signals", signal_id + "," + other_id,
                 "--approve-persona-cares", "--stamp")
        shutil.copyfile(proposal / "adapters.md", post / "adapters.md")
        self.assertEqual(before, {name: digest(self.shared / name) for name in before})
        self.cli("build_pairings", "--shared", post)
        report = self.cli("validate_setup", "--shared", post, "--source", source["source"])
        self.assertEqual(report["messaging"]["state"], "checks_passed")
        self.assertEqual(report["connectors"]["state"], "not_verified")
        factory.write(run / "validation.json", report)
        receipt = {"account_name": "Example Account", "account_aliases": ["Example Account"], "account_domain": "example.org",
                   "source_url": "https://example.org/news", "published_date": NOW.date().isoformat(), "quote": quote,
                   "evidence_subject": "Example Account", "signal_type": signal_id, "quote_speaker": "account"}
        factory.write(run / "receipt.json", receipt)
        (run / "public-signal.txt").write_text(quote)
        qualified = self.cli("evidence_gate", "--receipt", run / "receipt.json", "--page", run / "public-signal.txt",
                             "--policy", post / "policy.json", "--checked-at", NOW.isoformat(), "--now", NOW.isoformat())
        packet = {"bundle": {**qualified["bundle"], "vertical": vertical},
                  "claim": {"id": row["id"], "evidence": evidence, "persona": persona,
                            "pick_reason": "The account explicitly names work supported by this offer capability."},
                  "recipient": {"email": "buyer@example.org", "name": "Alex", "title": title, "source": "existing CRM Contact"},
                  "activity": [], "activity_complete": True, "voice_anchor_reference": "supplied:synthetic-voice",
                  "draft": {"subject": "Your market plan", "body": "Hi Alex,\n\nYour expansion plan suggests a workflow review. " + track + "\n\nWould a workflow review be useful?\n\nBest,\nSeller"}}
        if business == "cleaning":
            packet["draft"] = {"subject": "Cleaning for the new office", "body": "Hi Alex,\n\nYour office opening calls for cleaning coverage. " + track + "\n\nWould a site visit help you plan coverage?\n\nBest,\nSeller"}
        factory.write(run / "packet.json", packet)
        self.cli("outreach_gate", "--shared", post, "--packet", run / "packet.json", "--now", NOW.isoformat())
        return run, post, source, packet

    def review(self, run, post):
        names = ("policy.json", "claims.json", "taxonomy.json", "icp.md", "adapters.md")
        artifacts = ["postimages/" + name for name in names] + ["validation.json", "packet.json", "voice.txt",
                    "source/source-manifest.json", "source/materials/product.txt"]
        after = {"A1": {"_shared/" + name: digest(post / name) for name in names}}
        (run / "01_review.md").write_text("---\nstatus: ready\nartifacts: " + json.dumps(artifacts) +
                                         "\nexpected_after: " + json.dumps(after) + "\n---\n\n## Effect A1\nSynthetic installation only.\n")
        factory.write(run / "inputs.json", {"schema_version": 1, "effects": {"A1": {
            "kind": "configuration", "input": "postimages"}}, "gaps": [], "postimages": "postimages",
            "source_revision": factory.claim_document(post)["source_revision"], "setup_result": "validation.json"})
        self.assertEqual(self.cli("runs", "status", run.name)["state"], "awaiting_human_review")
        self.cli("runs", "record-review", run.name, "--reviewer", "Synthetic test", "--approval-ref", "test-only", "--effects", "A1",
                 "--source", factory.read(post / "policy.json")["refresh"]["source"])
        return names

    def test_product_and_service_businesses_install_their_own_mapping(self):
        products = []
        for business in ("research", "localization", "cleaning"):
            with self.subTest(business=business):
                run, post, source, packet = self.configure(business)
                names = self.review(run, post)
                self.assertEqual(self.cli("runs", "status", run.name)["state"], "review_current")
                for name in names:
                    shutil.copyfile(post / name, self.shared / name)
                self.assertEqual(self.cli("runs", "status", run.name)["state"], "recovery_required")
                review = factory.read(run / "review.json")
                factory.write(run / "02_result.json", {"recorded_at": NOW.isoformat(), "summary": "Synthetic configuration installed.",
                    "review_snapshot": review["snapshot"], "effects": [{"id": "A1", "status": "verified",
                    "provider_reference": "local-shared", "readback_reference": "synthetic-hashes"}]})
                self.assertEqual(self.cli("runs", "status", run.name)["state"], "completion_recorded")
                self.cli("validate_setup", "--source", source["source"])
                policy = factory.read(self.shared / "policy.json")
                self.assertFalse(policy["adoption"]["enabled"])
                self.assertFalse(policy["arr_growth"]["enabled"])
                products.append(packet["claim"]["id"])
                # The second company cannot use the first company's installed claim.
                if business == "localization":
                    packet["claim"]["id"] = products[0]
                    factory.write(run / "cross-company.json", packet)
                    result = self.cli("outreach_gate", "--packet", run / "cross-company.json", "--now", NOW.isoformat(), code=1)
                    self.assertIn("claim id not in claims.json", " ".join(result["reasons"]))
        self.assertEqual(len(set(products)), 3)
        self.cli("check_repo")
        self.assertEqual(self.public, {str(p): digest(self.root / p) for p in check_repo.public_files(self.root)})

    def test_shipped_examples_and_setup_use_the_discovery_query_schema(self):
        policy, claims, icp = factory.read(self.shared / "policy.json"), factory.claim_document(self.shared), factory.frontmatter(self.shared)
        tax = factory.taxonomy(self.shared)
        validate_setup.structure(policy, claims, tax, icp)
        signal = tax["signals"][0]
        signal["query_templates"] = signal.pop("example_queries")
        with self.assertRaises(ValueError):
            validate_setup.structure(policy, claims, tax, icp)
        signal["example_queries"] = []
        with self.assertRaises(ValueError):
            validate_setup.structure(policy, claims, tax, icp)

    def test_weak_binding_is_disclosed_and_block_mode_holds_it(self):
        run, post, source, packet = self.configure()
        row = factory.claim_document(post)["claims"][1]
        packet["claim"].update(id=row["id"], evidence=row["evidence"], pick_reason="Best guess: access review does not directly answer market planning.")
        packet["draft"]["body"] = "Hi Alex,\n\n" + row["track"] + " Could access review be relevant to your plan?\n\nBest,\nSeller"
        factory.write(run / "weak.json", packet)
        result = self.cli("outreach_gate", "--shared", post, "--packet", run / "weak.json", "--now", NOW.isoformat())
        self.assertIn("outside the market_entry binding", " ".join(result["flags"]))
        policy = factory.read(post / "policy.json")
        policy["outreach"]["fit_mode"] = "block"
        factory.write(post / "policy.json", policy)
        self.cli("outreach_gate", "--shared", post, "--packet", run / "weak.json", "--now", NOW.isoformat(), code=1)

    def test_readiness_detects_broken_evidence_stamps_references_and_voice(self):
        run, post, source, packet = self.configure()
        changes = [("claims.json", lambda d: d["claims"][0].update(evidence="An unsupported assertion.")),
                   ("claims.json", lambda d: d["claims"][0].update(personas=["unknown"])),
                   ("claims.json", lambda d: d["claims"][0].update(approved=None)),
                   ("taxonomy.json", lambda d: d["signals"][0].update(claim_ids=["unknown"])),
                   ("policy.json", lambda d: d["email_voice"].update(anchor_reference=None)),
                   ("policy.json", lambda d: d["outreach"].update(activity_lookback_days=1)),
                   ("policy.json", lambda d: d["outreach"]["lint"].pop("forbidden_phrases")),
                   ("policy.json", lambda d: d.pop("scan"))]
        for name, edit in changes:
            with self.subTest(name=name, edit=edit):
                path, before = post / name, (post / name).read_bytes()
                doc = factory.read(path)
                edit(doc)
                factory.write(path, doc)
                report = self.cli("validate_setup", "--shared", post, "--source", source["source"], code=1)
                self.assertTrue(report["messaging"]["issues"])
                path.write_bytes(before)
        self.cli("validate_setup", "--shared", post, code=1)

    def test_update_keeps_prior_history_and_preserves_active_configuration(self):
        run, post, source, packet = self.configure()
        for name in ("policy.json", "claims.json", "taxonomy.json", "icp.md", "adapters.md"):
            shutil.copyfile(post / name, self.shared / name)
        active = {p.name: digest(p) for p in self.shared.iterdir() if p.is_file()}
        original = Path(source["source"]) / "materials/product.txt"
        before = original.read_bytes()
        (run / "product.txt").write_bytes(before + b"Additional documented source context.\n")
        next_source = self.cli("source_snapshot", "--manifest", run / "intake.json", "--destination", run / "source-next", "--previous", source["source"])
        self.assertEqual(original.read_bytes(), before)
        self.assertEqual(source_snapshot.git(Path(next_source["source"]), "show", source["revision"] + ":materials/product.txt"), before.decode().strip())
        proposed = run / "update-proposal"
        shutil.copytree(post, proposed)
        policy = factory.read(proposed / "policy.json")
        policy["refresh"]["source"] = next_source["source"]
        factory.write(proposed / "policy.json", policy)
        next_post = run / "update-postimages"
        self.cli("refresh_tracks", "--source", next_source["source"], "--revision", next_source["revision"],
                 "--shared", proposed, "--stage", next_post, "--stamp")
        self.cli("validate_setup", "--shared", next_post, "--source", next_source["source"])
        self.assertEqual(factory.read(next_post / "policy.json")["followup_signal"]["due_calendar_days"], 12)
        self.assertEqual(active, {p.name: digest(p) for p in self.shared.iterdir() if p.is_file()})
        self.review(run, post)
        # A concurrent active edit invalidates the reviewed installation.
        with (self.shared / "icp.md").open("a") as out:
            out.write("A concurrent targeting change.\n")
        self.assertEqual(self.cli("runs", "status", run.name)["state"], "review_stale")

    def test_source_snapshots_preserve_originals_and_reject_unsafe_intake(self):
        run = self.root / "output/intake"
        run.mkdir(parents=True)
        original = b"synthetic binary original\x00\xff"
        (run / "guide.bin").write_bytes(original)
        (run / "extracted.txt").write_text("Synthetic extraction, page one.\n")
        sources = [{"path": "guide.bin", "reference": "originals/guide.bin", "kind": "source", "origin": "Supplied file"},
                   {"path": "extracted.txt", "reference": "text/guide.txt", "kind": "extracted_text", "origin": "Page one", "derived_from": "originals/guide.bin"}]
        manifest = run / "intake.json"
        factory.write(manifest, {"sources": sources})
        result = self.cli("source_snapshot", "--manifest", manifest, "--destination", run / "source")
        self.assertEqual((Path(result["source"]) / "originals/guide.bin").read_bytes(), original)
        self.cli("source_snapshot", "--manifest", manifest, "--destination", run / "source", code=2)
        factory.write(manifest, {"sources": sources[:1]})
        self.cli("source_snapshot", "--manifest", manifest, "--destination", run / "next", "--previous", run / "source", code=2)
        for ref in ("../escape", ".git/config", ".gitattributes", "SOURCE-MANIFEST.JSON", "originals/guide.bin/child"):
            with self.subTest(ref=ref):
                mutated = copy.deepcopy(sources)
                mutated[1]["reference"] = ref
                factory.write(manifest, {"sources": mutated})
                self.cli("source_snapshot", "--manifest", manifest, "--destination", run / "unsafe", code=2)
        factory.write(manifest, {"sources": sources})
        self.cli("source_snapshot", "--manifest", manifest, "--destination", self.root / "public-source", code=2)
        (run / "linked.bin").symlink_to(run / "guide.bin")
        linked = copy.deepcopy(sources)
        linked[0]["path"] = "linked.bin"
        factory.write(manifest, {"sources": linked})
        self.cli("source_snapshot", "--manifest", manifest, "--destination", run / "linked-source", code=2)
        factory.write(manifest, {"sources": sources})
        (run / "escape").symlink_to(self.root)
        self.cli("source_snapshot", "--manifest", manifest, "--destination", run / "escape/escaped-source", code=2)


class PolicyValidationTests(unittest.TestCase):
    def setUp(self):
        self.policy = factory.read(ROOT / "_shared/policy.example.json")

    def test_all_consumed_settings_validate_before_use(self):
        factory.validate_policy(self.policy)
        changes = [lambda p: p["identity"].update(timezone="Unknown/Zone"),
                   lambda p: p["identity"].update(internal_domains=["exam\tple.com"]),
                   lambda p: p["outreach"]["lint"].update(no_markdown=1),
                   lambda p: p["followup_signal"]["task"].update(description="{unknown}"),
                   lambda p: p["scan"]["warm_engagement"].update(lookback_days=True),
                   lambda p: p["adoption"].update(approved_statements={"unknown": "A guessed sentence."}),
                   lambda p: p["refresh"].update(watch_dirs=["../outside"])]
        for change in changes:
            with self.subTest(change=change):
                value = copy.deepcopy(self.policy)
                change(value)
                with self.assertRaises(ValueError):
                    factory.validate_policy(value)

    def test_sections_do_not_require_unrelated_workflow_configuration(self):
        self.policy.pop("scan")
        self.policy.pop("arr_growth")
        factory.validate_policy(self.policy, ("identity", "outreach"))
        with self.assertRaises(ValueError):
            factory.validate_policy(self.policy)

    def test_deprecated_fixed_policy_accepts_only_historical_defaults(self):
        self.policy["routing"]["new"] = "propose account claim"
        self.policy["prospector"]["admission"] = "one tier1 or two distinct tier2 signals"
        factory.validate_policy(self.policy)
        for section, key in (("routing", "new"), ("prospector", "admission")):
            value = copy.deepcopy(self.policy)
            value[section][key] = "skip the fixed check"
            with self.assertRaises(ValueError):
                factory.validate_policy(value)

    def test_domain_and_mailbox_comparisons_reject_malformed_identity(self):
        self.assertEqual(factory.domain("EXAMPLE.COM."), "example.com")
        self.assertEqual(factory.email("Buyer@EXAMPLE.COM."), "buyer@example.com")
        for value in ("example.com..", "example.com\t", "https://example.com", ".example.com", "example.com:443"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                factory.domain(value)
        for value in (None, "Buyer <buyer@example.com>", "buyer..name@example.com", "buyer@example", "buyer@example.com,other@example.com"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                factory.email(value)


if __name__ == "__main__":
    unittest.main()
