"""Synthetic regression tests; no live services."""
import json
import subprocess
import sys
import tempfile
import unittest

from gate_fixtures import SCRIPTS, SHARED
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


if __name__ == "__main__":
    unittest.main()
