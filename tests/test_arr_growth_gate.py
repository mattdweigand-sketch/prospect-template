"""Synthetic regression tests; no live services."""
import copy
from datetime import date
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from gate_fixtures import SCRIPTS, SHARED
sys.path.insert(0, str(SCRIPTS))
import arr_growth_gate as ag  # noqa: E402

POLICY = ag.load_policy(SHARED)
OWNER = POLICY["identity"]["owner_id"]
HOUSE = POLICY["routing"]["house_owner_ids"][0]
TODAY = date(2026, 9, 21)

ROW = {
    "mapping_verified": True, "daily_coverage_verified": True, "activity_complete": True, "contacts_complete": True,
    "organization_id": "org-1", "organization_name": "Acme", "account_id": "account-1",
    "baseline_arr_usd": 1200.0, "current_arr_usd": 2400.0, "net_change_usd": 1200.0,
    "observed_dates": 31, "required_dates": 31,
    "subscription_platform": "web", "billing_email": "jane@example.org", "communications_enabled": True,
    "account": {"id": "account-1", "exists": True, "name": "Acme", "owner_id": OWNER, "owner_is_active": True,
                "open_opportunity_ids": [], "headcount": 1200, "headcount_source": "Account.NumberOfEmployees"},
    "contacts": [{"id": "contact-1", "email": "Jane@Example.org", "first_name": "Jane"}],
    "last_touch_date": None,
}


def row(**over):
    r = copy.deepcopy(ROW)
    for k, v in over.items():
        if k in ("account",):
            r["account"].update(v)
        else:
            r[k] = v
    if "account_id" in over:
        r["account"]["id"] = r["account_id"]
        r["organization_id"] = "org-" + r["account_id"]
    if "net_change_usd" in over: r["current_arr_usd"] = r["baseline_arr_usd"] + r["net_change_usd"]
    return r


def run(*rows):
    return ag.check({"data_through_date": "2026-09-20", "rows": list(rows)}, POLICY, today=TODAY, shared=SHARED)


class Allow(unittest.TestCase):
    def test_person_greeting_and_template(self):
        out = run(row())
        self.assertEqual(out["verdict"], "allow")
        d = out["selected"][0]["draft"]
        self.assertEqual(d["to"], "jane@example.org")
        self.assertEqual(d["subject"], POLICY["arr_growth"]["email_template"]["subject"])
        self.assertTrue(d["body"].startswith("Hi Jane,\n\n"))
        self.assertTrue(d["body"].endswith("Best,\nSeller"))
        self.assertEqual(out["shortfall"], POLICY["arr_growth"]["max_accounts"] - 1)

    def test_team_greeting_when_no_contact(self):
        out = run(row(contacts=[]))
        self.assertTrue(out["selected"][0]["draft"]["body"].startswith("Hi Acme team,"))
        self.assertIsNone(out["selected"][0]["contact_id"])

    def test_team_greeting_when_first_name_blank(self):
        out = run(row(contacts=[{"id": "contact-1", "email": "jane@example.org", "first_name": " "}]))
        self.assertTrue(out["selected"][0]["draft"]["body"].startswith("Hi Acme team,"))

    def test_no_amounts_in_draft(self):
        d = run(row())["selected"][0]["draft"]
        self.assertIsNone(ag.FORBIDDEN.search(d["subject"]))
        self.assertIsNone(ag.FORBIDDEN.search(d["body"].split("\n\n", 1)[1]))

    def test_cap_and_order(self):
        rows = [row(account_id=f"account-{i}", net_change_usd=1000 - i) for i in range(4)]
        out = run(*rows)
        self.assertEqual(len(out["selected"]), POLICY["arr_growth"]["max_accounts"])
        self.assertEqual([s["rank"] for s in out["selected"]], [1, 2])
        self.assertEqual({h["hold"] for h in out["held"]}, {"over_max_accounts"})

    def test_old_touch_allows(self):
        out = run(row(last_touch_date="2026-08-01"))
        self.assertEqual(out["verdict"], "allow")

    def test_equal_growth_uses_account_id_ties_before_cap(self):
        rows = [row(account_id=f"account-{i}", net_change_usd=1200) for i in (1, 2, 3)]
        self.assertEqual([r["account_id"] for r in run(*rows)["selected"]], ["account-1", "account-2"])
        with self.assertRaisesRegex(ValueError, "then account ID"):
            run(*reversed(rows))

    def test_account_loader_does_not_require_taxonomy(self):
        with tempfile.TemporaryDirectory() as directory:
            shared = Path(directory)
            for name in ("policy.json", "icp.md"):
                shutil.copyfile(SHARED / name, shared / name)
            result = ag.check({"data_through_date": "2026-09-20", "rows": [row()]}, POLICY, TODAY, shared)
            self.assertEqual(result["verdict"], "allow")

    def test_canonical_email_comparison_preserves_original_recipient(self):
        r = row(billing_email="Jane@EXAMPLE.ORG.")
        self.assertEqual(run(r)["selected"][0]["draft"]["to"], "Jane@EXAMPLE.ORG.")


class Hold(unittest.TestCase):
    def hold(self, r):
        out = run(r)
        self.assertEqual(out["verdict"], "block")
        return out["held"][0]["hold"]

    def test_incomplete_coverage(self):
        self.assertEqual(self.hold(row(observed_dates=30)), "incomplete_daily_coverage")

    def test_nonpositive(self):
        self.assertEqual(self.hold(row(net_change_usd=0)), "no_positive_net_change")

    def test_no_account(self):
        self.assertEqual(self.hold(row(account={"exists": False})), "no_crm_account")

    def test_open_opp(self):
        self.assertEqual(self.hold(row(account={"open_opportunity_ids": ["deal-1"]})), "active_deal")

    def test_house_owner(self):
        self.assertEqual(self.hold(row(account={"owner_id": HOUSE})), "claim_transfer")

    def test_other_owner(self):
        self.assertEqual(self.hold(row(account={"owner_id": "other-owner"})), "owned_elsewhere")

    def test_territory_unknown(self):
        self.assertEqual(self.hold(row(account={"headcount": None})), "territory_unknown")

    def test_territory_out(self):
        self.assertEqual(self.hold(row(account={"headcount": 50000})), "territory_out")

    def test_billing_email_missing(self):
        self.assertEqual(self.hold(row(billing_email=None)), "billing_email_missing")

    def test_platform(self):
        self.assertEqual(self.hold(row(subscription_platform="ios")), "unsupported_billing_platform")

    def test_communications(self):
        self.assertEqual(self.hold(row(communications_enabled=False)), "communications_disabled")

    def test_ambiguous_contact(self):
        c = ROW["contacts"][0]
        self.assertEqual(self.hold(row(contacts=[c, {**c, "id": "contact-2"}])), "ambiguous_contact")

    def test_contact_email_mismatch(self):
        self.assertEqual(self.hold(row(contacts=[{"id": "contact-1", "email": "bob@example.org", "first_name": "Bob"}])),
                         "contact_email_mismatch")

    def test_recent_touch(self):
        self.assertEqual(self.hold(row(last_touch_date="2026-09-15")), "suppressed_recent_touch")

    def test_held_rows_carry_no_draft(self):
        out = run(row(observed_dates=30))
        self.assertNotIn("draft", out["held"][0])

    def test_unresolved_mapping_nulls_remain_held_without_false_duplicates(self):
        unresolved = row(mapping_verified=False)
        unresolved.update(organization_id=None, account_id=None)
        unresolved["account"]["id"] = None
        out = run(unresolved, copy.deepcopy(unresolved), row())
        self.assertEqual(out["verdict"], "allow")
        self.assertEqual([r["hold"] for r in out["held"]], ["ambiguous_account_mapping"] * 2)
        self.assertEqual([r["account_id"] for r in out["selected"]], ["account-1"])

    def test_unknown_count_and_source_are_an_explicit_hold(self):
        self.assertEqual(self.hold(row(account={"headcount": None, "headcount_source": None})), "territory_unknown")


class Input(unittest.TestCase):
    def test_missing_key(self):
        r = row()
        del r["contacts"]
        with self.assertRaises(ValueError):
            run(r)

    def test_forbidden_template_detected(self):
        for text in ("Your ARR is up 20%.", "Your arr increased.", "Annual\nrecurring revenue increased."):
            pol = copy.deepcopy(POLICY)
            pol["arr_growth"]["email_template"]["body"] = text
            with self.subTest(text=text), self.assertRaises(ValueError):
                ag.check({"data_through_date": "2026-09-20", "rows": [row()]}, pol, today=TODAY, shared=SHARED)

    def test_malformed_records_never_become_candidates(self):
        for changes in ({"account_id": None}, {"organization_id": None}, {"contacts": {}}, {"contacts": ""},
                        {"contacts": [{"id": None, "email": "jane@example.org"}]}, {"net_change_usd": True},
                        {"observed_dates": True}, {"communications_enabled": "true"},
                        {"billing_email": "jane@example.org,bob"}):
            r = row()
            r.update(changes)
            if "account_id" in changes:
                r["account"]["id"] = changes["account_id"]
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                run(r)

    def test_missing_source_and_noncanonical_dates_are_unusable(self):
        r = row()
        del r["account"]["headcount_source"]
        with self.assertRaisesRegex(ValueError, "headcount_source"):
            run(r)
        for value in ("20260920", "2026-09-20T00:00:00Z", None):
            with self.subTest(date=value), self.assertRaises(ValueError):
                ag.check({"data_through_date": value, "rows": [row()]}, POLICY, TODAY, SHARED)

    def test_direct_call_validates_enabled_module_configuration(self):
        policy = copy.deepcopy(POLICY)
        del policy["arr_growth"]["allowed_platforms"]
        with self.assertRaises(ValueError):
            ag.check({"data_through_date": "2026-09-20", "rows": [row()]}, policy, TODAY, SHARED)


if __name__ == "__main__":
    unittest.main()
