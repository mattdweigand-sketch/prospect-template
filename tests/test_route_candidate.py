"""Synthetic regression tests; no live services."""
import json
import copy
from datetime import datetime, timedelta
import subprocess
import sys
import tempfile
import unittest

from gate_fixtures import SCRIPTS, SHARED, make_shared
sys.path.insert(0, str(SCRIPTS))
import route_candidate as rc  # noqa: E402

RULES = rc.load_rules(SHARED)
T1 = [{"signal_type": "public_operations_initiative", "tier": "tier1"}]
T2 = [{"signal_type": "executive_statements", "tier": "tier2"}]


def receipt(**kw):
    base = {"domain": "example.org", "headcount": 1200, "signals": T1, "account_exists": False,
            "owner_id": None, "owner_is_active": None, "open_opportunity_ids": []}
    base.update(kw)
    return base


class RouteCandidateTests(unittest.TestCase):
    def test_rules_load_from_shared_files(self):
        self.assertEqual(RULES["owner"], "owner-1")
        self.assertEqual((RULES["min_emp"], RULES["max_emp"]), (200, 5000))
        self.assertEqual(len(RULES["house"]), 2)

    def test_no_account_claim_new_claimable(self):
        out = rc.check(receipt(), RULES)
        self.assertEqual((out["route"], out["claimable"], out["territory"]), ("claim_new", True, "in"))

    def test_one_tier2_not_admitted(self):
        out = rc.check(receipt(signals=T2), RULES)
        self.assertFalse(out["admitted"]); self.assertFalse(out["claimable"])

    def test_two_tier2_admitted(self):
        self.assertTrue(rc.check(receipt(signals=T2 + [{"signal_type": "supplier_partnership", "tier": "tier2"}]), RULES)["admitted"])

    def test_tier3_never_admits(self):
        t3 = [{"signal_type": "generic_marketing", "tier": "tier3"}] * 3
        self.assertFalse(rc.check(receipt(signals=t3), RULES)["admitted"])

    def test_unknown_headcount_blocks_claim(self):
        out = rc.check(receipt(headcount=None), RULES)
        self.assertEqual((out["territory"], out["claimable"]), ("unknown", False))

    def test_out_of_territory_blocks_claim(self):
        out = rc.check(receipt(headcount=12000), RULES)
        self.assertEqual((out["territory"], out["route"], out["claimable"]), ("out", "claim_new", False))

    def test_owner_owned_no_opp_is_scan(self):
        out = rc.check(receipt(account_exists=True, owner_id=RULES["owner"], owner_is_active=True), RULES)
        self.assertEqual((out["route"], out["claimable"]), ("scan", False))

    def test_owner_owned_open_opp_is_active_deal(self):
        out = rc.check(receipt(account_exists=True, owner_id=RULES["owner"], owner_is_active=True,
                               open_opportunity_ids=["deal-1"]), RULES)
        self.assertEqual(out["route"], "active_deal")

    def test_inactive_owner_claim_transfer(self):
        out = rc.check(receipt(account_exists=True, owner_id="other-owner", owner_is_active=False), RULES)
        self.assertEqual((out["route"], out["claimable"]), ("claim_transfer", True))

    def test_house_owner_claim_transfer(self):
        house = sorted(RULES["house"])[0]
        out = rc.check(receipt(account_exists=True, owner_id=house, owner_is_active=True), RULES)
        self.assertEqual(out["route"], "claim_transfer")

    def test_other_active_owner_owned_elsewhere(self):
        out = rc.check(receipt(account_exists=True, owner_id="other-owner", owner_is_active=True), RULES)
        self.assertEqual((out["route"], out["claimable"]), ("owned_elsewhere", False))

    def test_existing_account_without_owner_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(account_exists=True), RULES)

    def test_extra_key_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(score=9), RULES)

    def test_normalized_internal_domains_and_invalid_hosts(self):
        for domain in ("EXAMPLE.COM.", "team.example.com."):
            self.assertEqual(rc.check(receipt(domain=domain), RULES)["route"], "internal_domain")
        for domain in ("example.com\t", "example.com\n", "https://example.org", "example..org", "example.org:443"):
            with self.subTest(domain=domain), self.assertRaises(ValueError):
                rc.check(receipt(domain=domain), RULES)
        self.assertEqual(rc.check(receipt(domain="EXAMPLE.ORG."), RULES)["domain"], "example.org")

    def test_malformed_owner_and_opportunity_records_are_unusable(self):
        cases = [dict(account_exists=True, owner_id=v, owner_is_active=False) for v in (None, "", [], ["owner-2"], 1)]
        cases += [dict(owner_id="owner-2"), dict(owner_is_active=False), dict(open_opportunity_ids=["deal-1"])]
        cases += [dict(account_exists=True, owner_id="owner-2", owner_is_active=True, open_opportunity_ids=v)
                  for v in (None, "deal-1", [None], [1], [""])]
        cases += [dict(signals=[{"signal_type": [], "tier": "tier1"}]), dict(signals=[{"signal_type": "executive_statements", "tier": []}])]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                rc.check(receipt(**changes), RULES)

    def test_account_rules_do_not_require_taxonomy(self):
        with tempfile.TemporaryDirectory() as directory:
            shared = make_shared(directory)
            (shared / "taxonomy.json").unlink()
            self.assertEqual(rc.load_account_rules(shared)["owner"], "owner-1")

    def test_optional_existing_account_id_for_adoption_identity(self):
        self.assertEqual(rc.check(receipt(account_exists=True, account_id="account-1", owner_id="owner-1", owner_is_active=True), RULES)["route"], "scan")
        self.assertTrue(rc.check(receipt(account_id=None), RULES)["claimable"])
        for changes in (dict(account_id="account-1"), dict(account_exists=True, account_id=None, owner_id="owner-1", owner_is_active=True)):
            with self.assertRaises(ValueError):
                rc.check(receipt(**changes), RULES)

    def test_conflicting_legacy_admission_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            shared = make_shared(directory)
            policy = json.loads((shared / "policy.json").read_text())
            policy["prospector"]["admission"] = "three tier2 signals"
            (shared / "policy.json").write_text(json.dumps(policy))
            with self.assertRaises(ValueError):
                rc.load_rules(shared)

    def test_icp_rules_load(self):
        self.assertEqual(RULES["vertical_rank"]["professional_services"], 1)
        self.assertIn("unsupported_service_requirement", RULES["hard_dq"])
        self.assertIn("existing_solution_meets_need", RULES["recoverable_dq"])

    def test_vertical_rank_emitted(self):
        out = rc.check(receipt(vertical="legal"), RULES)
        self.assertEqual((out["vertical_rank"], out["claimable"]), (3, True))

    def test_no_vertical_is_null_rank(self):
        self.assertIsNone(rc.check(receipt(), RULES)["vertical_rank"])

    def test_unknown_vertical_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(vertical="fintech"), RULES)

    def test_hard_disqualifier_blocks_claim(self):
        out = rc.check(receipt(disqualifiers=["unsupported_service_requirement"]), RULES)
        self.assertEqual((out["route"], out["claimable"], out["hard_disqualifiers"]),
                         ("claim_new", False, ["unsupported_service_requirement"]))

    def test_recoverable_blocker_reported_not_blocking(self):
        out = rc.check(receipt(disqualifiers=["existing_solution_meets_need"]), RULES)
        self.assertEqual((out["claimable"], out["recoverable_blockers"]), (True, ["existing_solution_meets_need"]))

    def test_unknown_disqualifier_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(disqualifiers=["bad_vibes"]), RULES)

    def test_cli_exit_codes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=SHARED) as f:
            json.dump(receipt(), f)
        p = subprocess.run([sys.executable, str(SCRIPTS / "route_candidate.py"), "--receipt", f.name, "--shared", str(SHARED)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)["route"], "claim_new")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=SHARED) as f:
            f.write("nope")
        p = subprocess.run([sys.executable, str(SCRIPTS / "route_candidate.py"), "--receipt", f.name, "--shared", str(SHARED)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


class ScanRouteTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((SHARED / "policy.json").read_text())
        self.policy["scan"]["warm_engagement"].update(lookback_days=45, ignored_owner_ids=["integration"])
        self.now = datetime.fromisoformat("2026-09-21T12:00:00-07:00")
        self.packet = {"account": {"id": "account-1", "name": "Example", "domain": "example.org",
            "owner_id": "owner-1", "owner_is_active": True, "open_opportunity_ids": []},
            "tasks": [], "crm_complete": True, "tasks_complete": True,
            "activity_since": (self.now.date() - timedelta(days=45)).isoformat(), "read_reference": "complete-crm-read"}

    def run_route(self):
        return rc.scan_route(self.packet, self.policy, self.now)

    def task(self, owner="other-owner", days=40, subject="Re: planning"):
        return {"id": "task-1", "owner_id": owner, "subject": subject,
                "created_at": (self.now - timedelta(days=days)).isoformat()}

    def test_warm_task_between_windows_stops_handoff(self):
        self.packet["tasks"] = [self.task()]
        result = self.run_route()
        self.assertEqual((result["required_lookback_days"], result["route"], result["handoff_eligible"]), (45, "warm_engaged", False))
        self.assertEqual(result["warm_tasks"], self.packet["tasks"])

    def test_insufficient_history_or_incomplete_reads_are_limited(self):
        for field, value in (("activity_since", (self.now.date() - timedelta(days=30)).isoformat()),
                             ("crm_complete", False), ("tasks_complete", False), ("account", None),
                             ("read_reference", None)):
            original = copy.deepcopy(self.packet)
            self.packet[field] = value
            self.assertFalse(self.run_route()["handoff_eligible"])
            self.packet = original

    def test_own_and_ignored_activity_do_not_stop_scan(self):
        for owner in ("owner-1", "integration"):
            self.packet["tasks"] = [self.task(owner=owner)]
            self.assertTrue(self.run_route()["handoff_eligible"])
            self.assertEqual(self.run_route()["other_owner_ids"], [])

    def test_open_deal_precedes_warm_and_other_owner(self):
        self.packet["account"].update(owner_id="other-owner", open_opportunity_ids=["deal-1"])
        self.packet["tasks"] = [self.task()]
        self.assertEqual(self.run_route()["route"], "active_deal")

    def test_other_owner_and_internal_domains_never_handoff(self):
        self.packet["account"]["owner_id"] = "other-owner"
        self.assertEqual(self.run_route()["route"], "owned_elsewhere")
        self.packet["account"]["domain"] = "example.com."
        self.assertEqual(self.run_route()["route"], "internal_domain")

    def test_warm_boundary_and_nonmatching_subject(self):
        for days, subject, expected in ((45, "Re: planning", "warm_engaged"),
                                        (46, "Re: planning", "scan"), (1, "Planning", "scan")):
            self.packet["tasks"] = [self.task(days=days, subject=subject)]
            self.assertEqual(self.run_route()["route"], expected)

    def test_invalid_task_and_clock_inputs_raise(self):
        for task in ({}, {**self.task(), "created_at": "2026-09-20"}, {**self.task(), "owner_id": None},
                     self.task(days=-1)):
            self.packet["tasks"] = [task]
            with self.assertRaises(ValueError):
                self.run_route()
        with self.assertRaises(ValueError):
            rc.scan_route(self.packet, self.policy, self.now.replace(tzinfo=None))


if __name__ == "__main__":
    unittest.main()
