"""Fresh-install CLI handoffs for all seven workflows; provider evidence is synthetic.

The real helpers run in a temporary copy of public template files. No deployment
configuration is loaded, no live service is called, and no real approval is recorded.
"""
import copy
from datetime import datetime, timedelta, timezone
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
from test_run_checks import crm, handoff

NOW = datetime(2026, 9, 22, 6, 30, tzinfo=timezone.utc)
DAY = NOW.date()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FreshInstall(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="prospect-integration-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.root = self.base / "repo"
        self.public = check_repo.public_files(ROOT)
        for rel in self.public:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)
        self.preimages = {str(rel): digest(self.root / rel) for rel in self.public}
        self.shared = self.root / "_shared"

    def command(self, args, code=0, cwd=None, stdin=None):
        result = subprocess.run(args, cwd=cwd or self.root, input=stdin, capture_output=True, text=True)
        self.assertEqual(result.returncode, code, f"{args}\n{result.stdout}\n{result.stderr}")
        return result.stdout

    def cli(self, script, *args, code=0, stdin=None):
        clock = ["--now", NOW.isoformat()] if script in ("evidence_gate", "outreach_gate", "followup_gate") or (script == "runs" and args[0] in ("record-review", "preflight")) else []
        out = self.command([sys.executable, "-B", "scripts/" + script + ".py", *map(str, args), *clock], code, stdin=stdin)
        try:
            return json.loads(out)
        except ValueError:
            return out

    def path(self, name):
        return self.root / "output" / name

    def state(self, name, expected):
        self.assertEqual(self.cli("runs", "status", name)["state"], expected)

    def review_and_complete(self, name, artifacts, effects=None, postimages=None, source=None, arr_packet=None):
        path = self.path(name)
        effects = effects or {}
        after = {"A1": {"_shared/" + key: digest(value) for key, value in postimages.items()}} if postimages else {}
        header = "---\nstatus: ready\nartifacts: " + json.dumps(artifacts) + "\n"
        if after:
            header += "expected_after: " + json.dumps(after) + "\n"
        text = header + "---\n\n# Synthetic test only\nNo real approval or provider event.\n"
        for key, payload in effects.items():
            text += "\n## Effect " + key + "\n" + json.dumps(payload, indent=2) + "\n"
        (path / "01_review.md").write_text(text)
        self.state(name, "awaiting_human_review")
        options = ["--source", source] if source else []
        options += ["--arr-packet", "-"] if arr_packet is not None else []
        self.cli("runs", "record-review", name, "--reviewer", "Synthetic test",
                 "--approval-ref", "synthetic-only", *options, "--effects", *effects,
                 stdin=json.dumps(arr_packet) if arr_packet is not None else None)
        self.state(name, "review_current")
        if postimages:
            for key, source in postimages.items():
                shutil.copyfile(source, self.shared / key)
            self.state(name, "recovery_required")
        review = json.loads((path / "review.json").read_text())
        write(path / "02_result.json", {
            "recorded_at": NOW.isoformat(), "summary": "Synthetic local result; no provider called.",
            "review_snapshot": review["snapshot"], "effects": [
                {"id": key, "status": "verified", "provider_reference": "synthetic-provider",
                 "readback_reference": "synthetic-readback"} for key in effects],
        })
        self.state(name, "completion_recorded")

    def refresh(self):
        source = self.base / "source"
        (source / "products").mkdir(parents=True)
        (source / "products/export.md").write_text("Example Product exports a report as CSV.\n")
        self.command(["git", "init", "-q"], cwd=source)
        self.command(["git", "add", "."], cwd=source)
        self.command(["git", "-c", "user.name=Synthetic Test", "-c", "user.email=test@example.org",
                      "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false", "commit", "-qm", "Synthetic source"], cwd=source)
        revision = self.command(["git", "rev-parse", "HEAD"], cwd=source).strip()
        path = self.path("signal-refresh")
        proposal, post = path / "proposal", path / "postimages"
        proposal.mkdir()
        for name in ("policy.json", "claims.json", "taxonomy.json", "icp.md"):
            shutil.copyfile(self.shared / name, proposal / name)
        claims = json.loads((proposal / "claims.json").read_text())
        claims["claims"][0].update(status="approved", source_reference="products/export.md", approval_reference="synthetic-only")
        write(proposal / "claims.json", claims)
        import factory
        fm = factory.frontmatter(proposal)
        fm["status"] = "configured"
        factory.write_frontmatter(proposal, fm)
        names = ("claims.json", "taxonomy.json", "icp.md")
        before = {name: digest(self.shared / name) for name in names}
        report = self.cli("refresh_tracks", "--source", source, "--revision", revision, "--shared", proposal,
                          "--stage", post, "--approve-rows", "csv_export", "--approve-signals",
                          "reporting_initiative,paid_individuals_present", "--approve-persona-cares", "--stamp")
        self.assertEqual(report["broken_rows"], [])
        self.assertEqual(report["missing_pages"], [])
        self.assertEqual(before, {name: digest(self.shared / name) for name in names})
        write(path / "source-report.json", report)
        write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "configuration", "input": "postimages"}}, "gaps": [],
                                      "postimages": "postimages", "source_revision": revision,
                                      "diagnostic": {"shared": "proposal", "result": "source-report.json", "revision": revision}})
        self.cli("build_pairings", "--shared", post)
        self.review_and_complete("signal-refresh", ["source-report.json"] + ["postimages/" + name for name in names],
                                 {"A1": {name: digest(post / name) for name in names}},
                                 {name: post / name for name in names}, source=source)
        report = self.cli("refresh_tracks", "--source", source, "--revision", revision)
        self.assertTrue(report["unchanged"])
        self.assertEqual(report["unstamped"], [])
        self.cli("build_pairings")

    def test_all_workflow_handoffs_from_fresh_examples(self):
        self.cli("check_repo")
        self.cli("wrappers", "--check")
        self.cli("wrappers")
        for example in self.shared.glob("*.example.*"):
            shutil.copyfile(example, example.with_name(example.name.replace(".example", "")))
        self.cli("check_repo")
        self.cli("build_pairings")
        self.cli("build_pairings", "--check")
        routes = json.loads((self.root / "scripts/wrapper-contract.json").read_text())["commands"]
        self.assertEqual(set(routes), {"prospect-setup", "signal-scan", "signal-prospector", "signal-user-scan", "signal-outreach",
                                      "signal-followup", "signal-arr-growth", "signal-refresh"})
        # Guided setup covers product and service businesses in test_setup.py.
        routes.pop("prospect-setup")
        for name in routes:
            self.cli("runs", "init", name, name)
            self.state(name, "draft")
            self.cli("runs", "record-review", name, "--reviewer", "Synthetic", "--approval-ref", "test", code=1)
        blocked = self.cli("arr_growth_gate", "--packet", "-", stdin="{}", code=1)
        self.assertEqual(blocked["reasons"], ["billing adapter disabled"])

        path = self.path("signal-scan")
        quote = "Example Account announced a reporting initiative for its operations team."
        receipt = {"account_name": "Example Account", "account_aliases": ["Example Account"],
                   "account_domain": "example.org", "source_url": "https://example.org/news", "published_date": DAY.isoformat(),
                   "quote": quote, "evidence_subject": "Example Account", "signal_type": "reporting_initiative", "quote_speaker": "account",
                   "checked_at": (NOW - timedelta(minutes=5)).isoformat()}
        write(path / "receipt.json", receipt)
        (path / "source.txt").write_text(quote + "\nSynthetic source only.\n")
        gate = self.cli("evidence_gate", "--receipt", path / "receipt.json", "--page", path / "source.txt",
                        "--checked-at", (NOW - timedelta(minutes=5)).isoformat())
        write(path / "gate.json", gate)
        verdict = self.cli("scan_verdict", path / "gate.json")
        self.assertEqual(verdict["recommended"], 1)
        write(path / "verdict.json", verdict)

        outreach = {"bundle": {**gate["bundle"], "vertical": "technology"},
                    "claim": {"id": "csv_export", "evidence": "Example Product exports a report as CSV.", "persona": "operations_owner",
                              "pick_reason": "The reporting initiative suggests evaluating CSV export; actual need is unverified."},
                    "recipient": {"email": "buyer@example.org", "name": "Alex", "title": "Operations", "source": "existing CRM Contact", "title_override": None},
                    "activity": [], "activity_complete": True, "voice_anchor_reference": "synthetic-voice",
                    "draft": {"subject": "Reporting exports", "body": "Hi Alex,\n\nYour reporting initiative suggests a workflow review. Example Product supports CSV report exports.\n\nWould export format be useful to discuss?\n\nBest,\nSeller"}}
        write(self.base / "outreach.json", outreach)
        self.assertEqual(self.cli("outreach_gate", "--packet", self.base / "outreach.json", code=1)["verdict"], "block")

        # Enable only synthetic private inputs in the temporary deployment.
        policy = json.loads((self.shared / "policy.json").read_text())
        policy["arr_growth"].update(enabled=True, email_template={"subject": "Reporting workflow", "greeting_person": "Hi {first_name},",
            "greeting_team": "Hi {account_name} team,", "body": "Would a reporting review be useful?\n\nBest,\nSeller"})
        policy["adoption"]["enabled"] = True
        policy["email_voice"]["anchor_reference"] = "synthetic-voice"
        policy["refresh"].update(source=str(self.base / "source"), watch_dirs=["products"])
        write(self.shared / "policy.json", policy)
        self.refresh()
        write(path / "crm.json", crm(policy, NOW))
        write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": [], "sources": [{"receipt": "receipt.json", "page": "source.txt", "result": "gate.json"}], "crm": "crm.json", "verdict": "verdict.json"})
        self.review_and_complete("signal-scan", ["receipt.json", "source.txt", "gate.json", "verdict.json"])

        path = self.path("signal-prospector")
        candidate = {"domain": "example.org", "headcount": 400,
                     "signals": [{"signal_type": gate["bundle"]["signal_type"], "tier": gate["bundle"]["tier"]}],
                     "account_exists": False, "owner_id": None, "owner_is_active": None, "open_opportunity_ids": [],
                     "vertical": "technology", "disqualifiers": []}
        write(path / "candidate.json", candidate)
        routing = self.cli("route_candidate", "--receipt", path / "candidate.json")
        self.assertTrue(routing["claimable"])
        self.assertEqual(routing["route"], "claim_new")
        write(path / "routing.json", routing)
        for ref in ("receipt.json", "source.txt", "gate.json"):
            shutil.copyfile(self.path("signal-scan") / ref, path / ref)
        write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "account_create", "input": "candidate.json"}}, "gaps": [],
                                      "sources": [{"receipt": "receipt.json", "page": "source.txt", "result": "gate.json"}],
                                      "candidates": [{"receipt": "candidate.json", "result": "routing.json", "sources": ["gate.json"]}]})
        self.review_and_complete("signal-prospector", ["candidate.json", "routing.json"],
                                 {"A1": {"operation": "synthetic account create", "name": "Example Account", "owner_id": "example-owner"}})

        path = self.path("signal-user-scan")
        adoption = {"account_name": "Example Account", "account_id": "account-1", "account_domain": "example.org",
                    "data_through_date": (DAY - timedelta(days=1)).isoformat(), "mapped_org_count": 1,
                    "org_subscribed": False, "org_paying": False, "org_service_types": [], "org_platforms": [],
                    "paid_individuals_exist": True, "adoption": "individuals_only", "source_reference": "synthetic-aggregate"}
        write(path / "adoption.json", adoption)
        write(path / "crm.json", crm(policy, NOW))
        write(path / "aggregate.json", {"success": True, "mapping_complete": True, "reference": "synthetic-aggregate", "checked_at": NOW.isoformat()})
        write(path / "inputs.json", {"schema_version": 1, "effects": {}, "gaps": [], "bundle": "adoption.json", "crm": "crm.json", "receipt": "aggregate.json"})
        self.assertEqual(self.cli("privacy_check", "--bundle", path / "adoption.json")["verdict"], "clean")
        self.review_and_complete("signal-user-scan", ["adoption.json"])

        # Neither a public receipt nor an old gate marker can substitute for private data.
        write(self.base / "private-signal.json", {**receipt, "signal_type": "paid_individuals_present"})
        self.assertEqual(self.cli("evidence_gate", "--receipt", self.base / "private-signal.json",
                                 "--page", self.path("signal-scan") / "source.txt", "--checked-at", NOW.isoformat(),
                                 code=1)["reason"], "signal_source_not_web")
        forged = copy.deepcopy(outreach)
        forged["bundle"]["signal_type"] = "paid_individuals_present"
        write(self.base / "private-outreach.json", forged)
        self.assertIn("bundle signal_type must use a web source",
                      self.cli("outreach_gate", "--packet", self.base / "private-outreach.json", code=1)["reasons"])

        path = self.path("signal-outreach")
        write(path / "packet.json", outreach)
        (path / "body.txt").write_text(outreach["draft"]["body"])
        self.cli("lint_draft", "--body", path / "body.txt")
        result = self.cli("outreach_gate", "--packet", path / "packet.json")
        self.assertEqual((result["verdict"], result["flags"]), ("allow", []))
        write(path / "gate.json", result)
        write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "draft", "input": "packet.json"}}, "gaps": [],
                                      "packet": "packet.json", "result": "gate.json", "handoff": handoff(self.root, self.path("signal-scan"), path, "gate.json")})
        self.review_and_complete("signal-outreach", ["packet.json", "body.txt", "gate.json"],
                                 {"A1": {"to": outreach["recipient"]["email"], **outreach["draft"]}})
        saved = (path / "packet.json").read_bytes()
        (path / "packet.json").write_bytes(saved + b"\n")
        self.state("signal-outreach", "review_stale")
        (path / "packet.json").write_bytes(saved)

        path = self.path("signal-followup")
        followup = {"sent": [{"message_id": "message-1", "thread_id": "thread-1", "subject": outreach["draft"]["subject"],
                              "sent_at": (NOW - timedelta(minutes=1)).isoformat(), "to": outreach["recipient"]["email"]}],
                    "sent_lookup_reference": "synthetic-send", "account": {"id": "account-1", "owner_id": "example-owner", "open_opportunity_ids": []},
                    "contacts": [{"id": "contact-1", "account_id": "account-1", "email": "buyer@example.org"}],
                    "contacts_complete": True, "tasks_complete": True, "tasks": [],
                    "signal": {"signal_type": outreach["bundle"]["signal_type"], "claim_id": outreach["claim"]["id"]}}
        write(path / "packet.json", {**followup, "sent": []})
        self.assertEqual(self.cli("followup_gate", "--packet", path / "packet.json", code=1)["reasons"], ["no sent proof"])
        write(path / "packet.json", followup)
        result = self.cli("followup_gate", "--packet", path / "packet.json")
        write(path / "gate.json", result)
        write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "task", "input": "packet.json"}}, "gaps": [], "mode": "standard",
                                      "packet": "packet.json", "result": "gate.json", "handoff": handoff(self.root, self.path("signal-outreach"), path, "packet.json")})
        self.review_and_complete("signal-followup", ["packet.json", "gate.json"], {"A1": result["task"]})
        write(self.base / "duplicate.json", {**followup, "tasks": [{"id": "task-1", **result["task"]}]})
        self.assertEqual(self.cli("followup_gate", "--packet", self.base / "duplicate.json", code=1)["verdict"], "block")

        path = self.path("signal-arr-growth")
        row = {"organization_id": "org-1", "organization_name": "Example Account", "account_id": "account-1",
               "baseline_arr_usd": 100, "current_arr_usd": 200, "net_change_usd": 100, "observed_dates": 31, "required_dates": 31,
               "subscription_platform": "web", "billing_email": "billing@example.org", "communications_enabled": True,
               "account": {"id": "account-1", "exists": True, "name": "Example Account", "owner_id": "example-owner",
                           "owner_is_active": True, "open_opportunity_ids": [], "headcount": 400, "headcount_source": "synthetic"},
               "contacts": [], "last_touch_date": None, "daily_coverage_verified": True, "mapping_verified": True,
               "contacts_complete": True, "activity_complete": True}
        result = self.cli("arr_growth_gate", "--packet", "-", "--today", DAY.isoformat(),
                          stdin=json.dumps({"data_through_date": (DAY - timedelta(days=1)).isoformat(), "rows": [row]}))
        self.assertEqual(len(result["selected"]), 1)
        draft = result["selected"][0]["draft"]
        write(path / "draft.json", draft)
        write(path / "selection.json", {"retention_authorized": True, "success": True, "reference": "synthetic-selection", "immutable_input_reference": "immutable-synthetic-snapshot-1", "input_reference_kind": "immutable_snapshot"})
        write(path / "inputs.json", {"schema_version": 1, "effects": {"A1": {"kind": "draft", "input": "draft.json"}}, "gaps": [],
                                      "drafts": [{"account_id": "account-1", "draft": "draft.json"}], "receipt": "selection.json"})
        self.review_and_complete("signal-arr-growth", ["draft.json"], {"A1": draft}, arr_packet={"data_through_date": (DAY - timedelta(days=1)).isoformat(), "rows": [row], "immutable_input_reference": "immutable-synthetic-snapshot-1", "input_reference_kind": "immutable_snapshot"})
        followup["signal"] = {"signal_type": "arr_growth", "claim_id": "arr_growth"}
        followup["sent"][0].update(to=draft["to"], subject=draft["subject"])
        followup["contacts"][0]["email"] = draft["to"]
        write(self.base / "growth-followup.json", followup)
        self.assertEqual(self.cli("followup_gate", "--packet", self.base / "growth-followup.json", "--mode", "arr_growth")["verdict"], "allow")

        for name in routes:
            self.state(name, "completion_recorded")
        self.cli("check_repo")
        self.cli("wrappers", "--check")
        self.assertEqual(self.preimages, {str(rel): digest(self.root / rel) for rel in check_repo.public_files(self.root)})


if __name__ == "__main__":
    unittest.main()
