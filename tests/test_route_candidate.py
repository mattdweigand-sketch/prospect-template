import _support
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SHARED = _support.SHARED
SCRIPTS = ROOT / "_shared" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import common  # noqa: E402
import route_candidate as rc  # noqa: E402

RULES = rc.load_rules(SHARED)
T1 = [{"signal_type": "announced_initiative", "tier": "tier1"}]
T2 = [{"signal_type": "leader_priority_statement", "tier": "tier2"}]
T3 = [{"signal_type": "generic_marketing", "tier": "tier3"}]
WH = [{"signal_type": "paid_individuals_present", "tier": "tier2"}]


def receipt(**kw):
    base = {"domain": "acme.example", "headcount": 1200, "signals": T1, "account_exists": False,
            "owner_id": None, "owner_is_active": None, "open_deal_ids": []}
    base.update(kw)
    return base


def run_cli(payload, raw=None):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "receipt.json"
        p.write_text(raw if raw is not None else json.dumps(payload))
        r = subprocess.run([sys.executable, str(SCRIPTS / "route_candidate.py"), "--receipt", str(p)],
                           capture_output=True, text=True)
    return r


class RouteCandidateTests(unittest.TestCase):
    def test_rules_load_from_shared_files(self):
        self.assertEqual(RULES["owner"], rc.common.load_policy(SHARED)["identity"]["crm_user_id"])
        self.assertEqual((RULES["min_emp"], RULES["max_emp"]), (50, 10000))
        self.assertEqual(len(RULES["house"]), 2)

    def test_rules_carry_taxonomy_types_and_admission(self):
        self.assertEqual(RULES["types"]["announced_initiative"]["tier"], "tier1")
        self.assertTrue(RULES["types"]["paid_individuals_present"]["source"])
        self.assertIsNone(RULES["types"]["leader_priority_statement"]["source"])
        self.assertEqual(RULES["admission"], {"tier1_min": 1, "tier2_min": 2, "warehouse_needs_web_tier2": True,
                                              "warehouse_max_counted": 1})

    def test_warehouse_max_counted_defaults_to_one(self):
        rules = dict(RULES, admission={k: v for k, v in RULES["admission"].items() if k != "warehouse_max_counted"})
        with mock.patch.object(rc.common, "load_taxonomy", return_value={"tiers": common.load_taxonomy(SHARED)["tiers"],
                                                                        "admission": rules["admission"]}):
            self.assertEqual(rc.load_rules(SHARED)["admission"]["warehouse_max_counted"], 1)

    def test_warehouse_max_counted_two_lets_two_warehouse_rows_count(self):
        max_one = dict(RULES, admission=dict(RULES["admission"], tier2_min=3))
        max_two = dict(RULES, admission=dict(RULES["admission"], tier2_min=3, warehouse_max_counted=2))
        self.assertFalse(rc.admission(WH + WH + T2, max_one)[0])      # 1 warehouse + 1 web, 2 of 3
        admitted, why = rc.admission(WH + WH + T2, max_two)
        self.assertTrue(admitted)                                    # 2 warehouse + 1 web, 3 of 3
        self.assertTrue(why.startswith("0 tier1, 3 tier2"))
        self.assertFalse(rc.admission(WH + WH, max_two)[0])          # still needs the web tier2

    def test_warehouse_max_counted_zero_never_counts_warehouse(self):
        rules = dict(RULES, admission=dict(RULES["admission"], warehouse_max_counted=0))
        admitted, why = rc.admission(WH + T2, rules)
        self.assertFalse(admitted)
        self.assertIn("at most 0 count", why)

    def test_no_account_claim_new_claimable(self):
        out = rc.check(receipt(), RULES)
        self.assertEqual((out["route"], out["claimable"], out["territory"]), ("claim_new", True, "in"))

    def test_one_tier2_not_admitted(self):
        out = rc.check(receipt(signals=T2), RULES)
        self.assertFalse(out["admitted"]); self.assertFalse(out["claimable"])

    def test_two_tier2_admitted(self):
        self.assertTrue(rc.check(receipt(signals=T2 + T2), RULES)["admitted"])

    def test_tier3_never_admits(self):
        out = rc.check(receipt(signals=T3 * 3), RULES)
        self.assertFalse(out["admitted"])
        self.assertTrue(rc.check(receipt(signals=T1 + T3), RULES)["admitted"])

    def test_two_warehouse_signals_not_admitted(self):
        out = rc.check(receipt(signals=WH + WH), RULES)
        self.assertEqual((out["admitted"], out["claimable"]), (False, False))
        self.assertIn("need one web tier2", out["admission"])

    def test_warehouse_plus_web_tier2_admitted(self):
        out = rc.check(receipt(signals=WH + T2), RULES)
        self.assertEqual((out["admitted"], out["claimable"]), (True, True))
        self.assertTrue(out["admission"].startswith("0 tier1, 2 tier2"))

    def test_warehouse_counts_once(self):
        out = rc.check(receipt(signals=WH + WH + T2), RULES)
        self.assertTrue(out["admitted"])
        self.assertIn("extra warehouse signal ignored", out["admission"])

    def test_warehouse_plus_web_tier1_admitted_on_tier1(self):
        self.assertTrue(rc.check(receipt(signals=WH + T1), RULES)["admitted"])

    def test_unknown_signal_type_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(signals=[{"signal_type": "vibes", "tier": "tier1"}]), RULES)

    def test_mis_tiered_signal_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(signals=[{"signal_type": "leader_priority_statement", "tier": "tier1"}]), RULES)

    def test_signal_without_shape_is_error(self):
        for bad in (["tier1"], [{"tier": "tier1"}], [{"signal_type": "announced_initiative"}]):
            with self.assertRaises(ValueError):
                rc.check(receipt(signals=bad), RULES)

    def test_unknown_headcount_blocks_claim(self):
        out = rc.check(receipt(headcount=None), RULES)
        self.assertEqual((out["territory"], out["claimable"]), ("unknown", False))

    def test_out_of_territory_blocks_claim(self):
        out = rc.check(receipt(headcount=12000), RULES)
        self.assertEqual((out["territory"], out["route"], out["claimable"]), ("out", "claim_new", False))

    def test_seller_owned_no_opp_is_scan(self):
        out = rc.check(receipt(account_exists=True, owner_id=RULES["owner"], owner_is_active=True), RULES)
        self.assertEqual((out["route"], out["claimable"]), ("scan", False))

    def test_seller_owned_open_opp_is_active_deal(self):
        out = rc.check(receipt(account_exists=True, owner_id=RULES["owner"], owner_is_active=True,
                               open_deal_ids=["006x"]), RULES)
        self.assertEqual(out["route"], "active_deal")

    def test_open_deal_precedes_every_existing_owner_route(self):
        for owner, active in ((sorted(RULES["house"])[0], True), ("005other", False), ("005other", True)):
            with self.subTest(owner=owner, active=active):
                out = rc.check(receipt(account_exists=True, owner_id=owner, owner_is_active=active,
                                       open_deal_ids=["006OPEN"]), RULES)
                self.assertEqual((out["route"], out["claimable"]), ("active_deal", False))

    def test_unknown_or_malformed_crm_reads_are_not_absence(self):
        for changes in ({"account_exists": None}, {"account_exists": "false"},
                        {"open_deal_ids": None}, {"open_deal_ids": [None]},
                        {"account_exists": True, "owner_id": RULES["owner"], "owner_is_active": None}):
            with self.subTest(changes=changes):
                out = run_cli(receipt(**changes))
                self.assertEqual(out.returncode, 2)
                self.assertEqual(json.loads(out.stdout)["verdict"], "error")
                self.assertEqual(out.stderr, "")

    def test_seller_owned_inactive_is_claim_transfer(self):
        out = rc.check(receipt(account_exists=True, owner_id=RULES["owner"], owner_is_active=False), RULES)
        self.assertEqual(out["route"], "claim_transfer")

    def test_inactive_owner_claim_transfer(self):
        out = rc.check(receipt(account_exists=True, owner_id="005other", owner_is_active=False), RULES)
        self.assertEqual((out["route"], out["claimable"]), ("claim_transfer", True))

    def test_house_owner_claim_transfer(self):
        house = sorted(RULES["house"])[0]
        out = rc.check(receipt(account_exists=True, owner_id=house, owner_is_active=True), RULES)
        self.assertEqual(out["route"], "claim_transfer")

    def test_other_active_owner_owned_elsewhere(self):
        out = rc.check(receipt(account_exists=True, owner_id="005other", owner_is_active=True), RULES)
        self.assertEqual((out["route"], out["claimable"]), ("owned_elsewhere", False))

    def test_existing_account_without_owner_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(account_exists=True), RULES)

    def test_extra_key_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(score=9), RULES)

    def test_icp_rules_load(self):
        self.assertEqual(RULES["vertical_rank"]["professional_services"], 1)
        self.assertIn("outside_offer_scope", RULES["hard_dq"])
        self.assertIn("unclear_relevant_need", RULES["recoverable_dq"])

    def test_vertical_rank_emitted(self):
        out = rc.check(receipt(vertical="retail"), RULES)
        self.assertEqual((out["vertical_rank"], out["claimable"]), (3, True))

    def test_no_vertical_is_null_rank(self):
        self.assertIsNone(rc.check(receipt(), RULES)["vertical_rank"])

    def test_unknown_vertical_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(vertical="fintech"), RULES)

    def test_hard_disqualifier_blocks_claim(self):
        out = rc.check(receipt(disqualifiers=["outside_offer_scope"]), RULES)
        self.assertEqual((out["route"], out["claimable"], out["hard_disqualifiers"]),
                         ("claim_new", False, ["outside_offer_scope"]))

    def test_recoverable_blocker_reported_not_blocking(self):
        out = rc.check(receipt(disqualifiers=["unclear_relevant_need"]), RULES)
        self.assertEqual((out["claimable"], out["recoverable_blockers"]), (True, ["unclear_relevant_need"]))

    def test_unknown_disqualifier_is_error(self):
        with self.assertRaises(ValueError):
            rc.check(receipt(disqualifiers=["bad_vibes"]), RULES)

    def test_cli_exit_codes(self):
        p = run_cli(receipt())
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["route"], "claim_new")
        p = run_cli(None, raw="nope")
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["verdict"], "error")

    def test_cli_bad_signal_shape_is_json_not_traceback(self):
        for payload in (receipt(signals=["tier1"]), receipt(signals=[{"signal_type": "vibes", "tier": "tier1"}]),
                        receipt(signals=WH + WH, account_exists=True, owner_id="x", owner_is_active=None)):
            p = run_cli(payload)
            self.assertEqual(p.returncode, 2, p.stdout)
            self.assertEqual(p.stderr, "")
            self.assertEqual(json.loads(p.stdout)["verdict"], "error")


if __name__ == "__main__":
    unittest.main()
