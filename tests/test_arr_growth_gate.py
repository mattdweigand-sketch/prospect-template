import _support
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SHARED = _support.SHARED
SCRIPTS = ROOT / "workflows" / "signal-arr-growth"
sys.path.insert(0, str(ROOT / "_shared" / "scripts"))
sys.path.insert(0, str(SCRIPTS))
import arr_growth_gate as ag  # noqa: E402
import common  # noqa: E402

POLICY = common.load_policy()
SELLER = POLICY["identity"]["crm_user_id"]
HOUSE = POLICY["crm"]["house_owner_ids"][0]
TODAY = date(2026, 9, 21)

ROW = {
    "organization_uuid": "org-1", "organization_name": "Acme", "crm_account_id": "001A",
    "currency": "USD", "baseline_arr_usd": 1200.0, "current_arr_usd": 2400.0, "net_change_usd": 1200.0,
    "observed_dates": 31, "required_dates": 31,
    "subscription_platform": "web", "billing_email": "jane@acme.example", "communications_enabled": True,
    "account": {"exists": True, "name": "Acme", "website": "https://acme.example", "owner_id": SELLER, "owner_is_active": True,
                "open_deal_ids": [], "headcount": 1200, "headcount_source": "account.headcount"},
    "contacts": [{"id": "003A", "email": "Jane@Acme.example", "first_name": "Jane"}],
    "last_touch_date": None,
    "reads": {"account": True, "deals": True, "headcount_lookup": True,
              "contacts": True, "tasks": True, "events": True, "email_sent": True},
}


def row(**over):
    r = copy.deepcopy(ROW)
    for k, v in over.items():
        if k in ("account", "reads"):
            r[k].update(v)
        else:
            r[k] = v
    return r


def run(*rows):
    return ag.check({"data_through_date": "2026-09-20", "rows": list(rows)}, POLICY, today=TODAY)


class Allow(unittest.TestCase):
    def test_unconverted_or_missing_currency_rejected(self):
        for currency in ('EUR', 'GBP', '', None):
            with self.subTest(currency=currency), self.assertRaisesRegex(ValueError, 'currency must be USD'):
                run(row(currency=currency))
        record = row(); del record['currency']
        with self.assertRaisesRegex(ValueError, 'currency'):
            run(record)

    def test_explicit_upstream_usd_normalization_is_compatible(self):
        # Synthetic EUR amounts converted upstream at a reviewed fixed rate. The gate
        # verifies declared units and arithmetic, not the provenance of that FX rate.
        record = row(currency='USD', baseline_arr_usd=1000 * 1.2,
                     current_arr_usd=2000 * 1.2, net_change_usd=1000 * 1.2)
        out = run(record)
        self.assertEqual(out['verdict'], 'allow')
        self.assertEqual(out['selected'][0]['currency'], 'USD')
        self.assertEqual(out['selected'][0]['net_change_usd'], 1200)

    def test_person_greeting_and_template(self):
        out = run(row())
        self.assertEqual(out["verdict"], "allow")
        d = out["selected"][0]["draft"]
        self.assertEqual(d["to"], "jane@acme.example")
        self.assertEqual(d["subject"], POLICY["arr_growth"]["draft"]["subject"])
        self.assertTrue(d["body"].startswith("Hi Jane,\n\n"))
        self.assertTrue(d["body"].endswith("Best,\nSeller"))
        self.assertEqual(out["shortfall"], POLICY["arr_growth"]["max_accounts_per_run"] - 1)

    def test_team_greeting_when_no_contact(self):
        out = run(row(contacts=[]))
        self.assertTrue(out["selected"][0]["draft"]["body"].startswith("Hi Acme team,"))
        self.assertIsNone(out["selected"][0]["contact_id"])

    def test_team_greeting_when_first_name_blank(self):
        out = run(row(contacts=[{"id": "003A", "email": "jane@acme.example", "first_name": " "}]))
        self.assertTrue(out["selected"][0]["draft"]["body"].startswith("Hi Acme team,"))

    def test_no_amounts_in_draft(self):
        d = run(row())["selected"][0]["draft"]
        forbid = ag.forbidden(POLICY["arr_growth"])
        self.assertIsNone(forbid.search(d["subject"]))
        self.assertIsNone(forbid.search(d["body"].split("\n\n", 1)[1]))

    def test_recipient_platform_comes_from_policy(self):
        pol = copy.deepcopy(POLICY)
        pol["arr_growth"]["recipient_platform"] = "ios"
        out = ag.check({"data_through_date": "2026-09-20", "rows": [row(subscription_platform="ios")]}, pol, today=TODAY)
        self.assertEqual(out["verdict"], "allow")
        self.assertEqual(ag.check({"data_through_date": "2026-09-20", "rows": [row()]}, pol, today=TODAY)["held"][0]["hold"], "unsupported_billing_platform")

    def test_cap_and_order(self):
        rows = [row(crm_account_id=f"001{i}", current_arr_usd=2200 - i, net_change_usd=1000 - i) for i in range(4)]
        out = run(*rows)
        self.assertEqual(len(out["selected"]), POLICY["arr_growth"]["max_accounts_per_run"])
        self.assertEqual([s["rank"] for s in out["selected"]], [1, 2])
        self.assertEqual({h["hold"] for h in out["held"]}, {"over_max_accounts_per_run"})

    def test_old_touch_allows(self):
        out = run(row(last_touch_date="2026-08-01"))
        self.assertEqual(out["verdict"], "allow")

    def test_suppression_boundary_matches_outreach(self):
        days = POLICY["arr_growth"]["suppression_days"]
        on_boundary = (TODAY - timedelta(days=days)).isoformat()
        past_boundary = (TODAY - timedelta(days=days + 1)).isoformat()
        self.assertEqual(run(row(last_touch_date=on_boundary))["held"][0]["hold"], "suppressed_recent_touch")
        self.assertEqual(run(row(last_touch_date=past_boundary))["verdict"], "allow")

    def test_default_today_is_policy_timezone(self):
        # 04:00 UTC on 09-22 is still 09-21 Pacific. A touch 30 days before 09-21 sits on the boundary and holds.
        # Under a UTC date it would be 31 days old and allow.
        fixed = datetime(2026, 9, 22, 4, 0, tzinfo=ZoneInfo("UTC")).astimezone(common.policy_tz(POLICY))
        with mock.patch.object(common, "policy_now", return_value=fixed):
            out = ag.check({"data_through_date": "2026-09-20", "rows": [row(last_touch_date="2026-08-22")]}, POLICY)
        self.assertEqual(out["held"][0]["hold"], "suppressed_recent_touch")


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
        self.assertEqual(self.hold(row(account={"open_deal_ids": ["006X"]})), "active_deal")

    def test_house_owner(self):
        self.assertEqual(self.hold(row(account={"owner_id": HOUSE})), "claim_transfer")

    def test_other_owner(self):
        self.assertEqual(self.hold(row(account={"owner_id": "005OTHER"})), "owned_elsewhere")

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
        self.assertEqual(self.hold(row(contacts=[c, {**c, "id": "003B"}])), "ambiguous_contact")

    def test_contact_email_mismatch(self):
        self.assertEqual(self.hold(row(contacts=[{"id": "003A", "email": "bob@acme.example", "first_name": "Bob"}])),
                         "contact_email_mismatch")

    def test_recent_touch(self):
        self.assertEqual(self.hold(row(last_touch_date="2026-09-15")), "suppressed_recent_touch")

    def test_held_rows_carry_no_draft(self):
        out = run(row(observed_dates=30))
        self.assertNotIn("draft", out["held"][0])


class Input(unittest.TestCase):
    def test_complete_data_date_required(self):
        for value in (None, "2020-01-01", "2030-01-01", "banana"):
            with self.subTest(date=value), self.assertRaisesRegex(ValueError, "complete data date"):
                ag.check({"data_through_date": value, "rows": [row()]}, POLICY, today=TODAY)

    def test_policy_sized_coverage_and_consistent_finite_growth(self):
        for changes, reason in (
            ({"observed_dates": 0, "required_dates": 0}, "incomplete_daily_coverage"),
            ({"observed_dates": True, "required_dates": True}, "incomplete_daily_coverage"),
            ({"baseline_arr_usd": 2400, "current_arr_usd": 1200}, "inconsistent_net_change"),
            ({"current_arr_usd": 1200, "net_change_usd": 0.001}, "inconsistent_net_change"),
        ):
            with self.subTest(changes=changes):
                self.assertEqual(run(row(**changes))["held"][0]["hold"], reason)

    def test_malformed_arr_amounts_are_errors(self):
        for changes in ({"baseline_arr_usd": -1}, {"current_arr_usd": float("inf")},
                        {"net_change_usd": float("nan")}, {"net_change_usd": True}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "finite, nonnegative"):
                run(row(**changes))

    def test_unknown_routing_facts_are_errors(self):
        for key in ("exists", "owner_is_active", "open_deal_ids"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                run(row(account={key: None}))

    def test_required_reads_and_headcount_lookup(self):
        for key in ("account", "deals", "contacts", "tasks", "events", "email_sent"):
            with self.subTest(read=key):
                self.assertEqual(run(row(reads={key: False}))["held"][0]["hold"], f"read_not_completed:{key}")
        self.assertEqual(run(row(reads={"headcount_lookup": False}))["verdict"], "allow")
        for facts in ({"headcount": None}, {"headcount_source": "company filing"}):
            self.assertEqual(run(row(account=facts, reads={"headcount_lookup": False}))["held"][0]["hold"],
                             "read_not_completed:headcount_lookup")

    def test_held_routes_and_territory_do_not_require_later_reads(self):
        for facts, reason in (({"open_deal_ids": ["006A"]}, "active_deal"),
                              ({"headcount": 50000}, "territory_out")):
            r = row(account=facts)
            r["reads"] = {"account": True, "deals": True}
            self.assertEqual(run(r)["held"][0]["hold"], reason)

    def test_duplicate_account_does_not_consume_another_selection(self):
        out = run(row(), row(organization_uuid="org-2"), row(crm_account_id="001B"))
        self.assertEqual([s["account_id"] for s in out["selected"]], ["001A", "001B"])
        self.assertEqual(out["held"][0]["hold"], "duplicate_account")
        self.assertEqual(out["shortfall"], 0)

    def test_missing_account_domain_holds(self):
        self.assertEqual(run(row(account={"website": None}))["held"][0]["hold"], "account_domain_missing")

    def test_literal_null_name_uses_team_greeting(self):
        r = row(contacts=[{"id": "003A", "email": "jane@acme.example", "first_name": " NULL "}])
        self.assertTrue(run(r)["selected"][0]["draft"]["body"].startswith("Hi Acme team,"))

    def test_missing_key(self):
        r = row()
        del r["contacts"]
        with self.assertRaises(ValueError):
            run(r)

    def test_forbidden_template_detected(self):
        pol = copy.deepcopy(POLICY)
        pol["arr_growth"]["draft"]["body"] = "Your ARR is up 20%."
        with self.assertRaises(ValueError):
            ag.check({"data_through_date": "2026-09-20", "rows": [row()]}, pol, today=TODAY)

    def test_forbidden_pattern_is_case_insensitive_and_from_policy(self):
        pol = copy.deepcopy(POLICY)
        pol["arr_growth"]["draft"]["body"] = "Your arr grew, congratulations."
        with self.assertRaises(ValueError):
            ag.check({"data_through_date": "2026-09-20", "rows": [row()]}, pol, today=TODAY)
        pol["arr_growth"]["draft_forbidden_pattern"] = "never"
        self.assertEqual(ag.check({"data_through_date": "2026-09-20", "rows": [row()]}, pol, today=TODAY)["verdict"], "allow")


class Queries(unittest.TestCase):
    ACCOUNT = {"id": "001000000000001AAA", "website": "HTTPS://www.Acme.example/path"}

    def test_read_intents_preserve_relationship_domain_and_policy_window(self):
        result = ag.queries({"accounts": [self.ACCOUNT]}, POLICY, today=TODAY)
        q = result["queries"][0]
        self.assertEqual(result["cutoff_date"], "2026-08-22")
        self.assertEqual(q["tasks"]["capability"], "crm.query")
        self.assertEqual(q["tasks"]["filters"], {"account_id":self.ACCOUNT["id"], "date_gte":"2026-08-22", "subtypes":["Email","Call"]})
        self.assertEqual(q["events"]["filters"], {"account_id":self.ACCOUNT["id"], "date_gte":"2026-08-22"})
        self.assertEqual(q["email_sent"]["filters"], {"is_sent":True, "recipient_domain":"acme.example", "sent_at_gte":"2026-08-22T00:00:00-07:00"})
        pol = copy.deepcopy(POLICY)
        pol["outreach"]["suppressing_task_subtypes"] = ["Phone Call"]
        self.assertEqual(ag.queries({"accounts":[self.ACCOUNT]},pol,TODAY)["queries"][0]["tasks"]["filters"]["subtypes"],["Phone Call"])

    def test_missing_domain_holds_and_opaque_ids_remain_data(self):
        for website in (None, "NULL", "user@acme.example", "https://acme.example' OR 1=1", "localhost"):
            with self.subTest(website=website):
                q = ag.queries({"accounts": [{**self.ACCOUNT, "website": website}]}, POLICY, TODAY)["queries"][0]
                self.assertEqual(q["hold"], "account_domain_missing")
                self.assertNotIn("email_sent", q)
        for aid in ("92384", "ca683b7c-bb36-4ed4-8108-94b0efea2ec3", "001' OR Id != null"):
            q=ag.queries({"accounts":[{**self.ACCOUNT,"id":aid}]},POLICY,TODAY)["queries"][0]
            self.assertEqual(q["tasks"]["filters"]["account_id"],aid)
        for aid in ("", " padded ", "bad\nID", 12, True):
            with self.assertRaises(ValueError):
                ag.queries({"accounts":[{**self.ACCOUNT,"id":aid}]},POLICY,TODAY)


class Cli(unittest.TestCase):
    def run_gate(self, packet):
        packet = {"data_through_date": "2026-09-20", **packet}
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "packet.json"
            f.write_text(json.dumps(packet))
            return subprocess.run([sys.executable, str(SCRIPTS / "arr_growth_gate.py"), "--packet", str(f), "--today", TODAY.isoformat()],
                                  capture_output=True, text=True)

    def test_exit_codes_and_envelopes(self):
        p = self.run_gate({"data_through_date": "2026-09-20", "rows": [row()]})
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(json.loads(p.stdout)["verdict"], "allow")
        p = self.run_gate({"data_through_date": "2026-09-20", "rows": [row(observed_dates=30)]})
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)["verdict"], "block")
        p = self.run_gate({"rows": "not a list"})
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertEqual(p.stderr, "")
        out = json.loads(p.stdout)
        self.assertEqual(out["verdict"], "error")
        self.assertIn("rows must be a list", out["reason"])
        r = row(); del r["contacts"]
        p = self.run_gate({"rows": [r]})
        self.assertEqual(p.returncode, 2)
        self.assertIn("row 1 missing keys", json.loads(p.stdout)["reason"])

    def test_queries_cli(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "accounts.json"
            f.write_text(json.dumps({"accounts": [Queries.ACCOUNT]}))
            p = subprocess.run([sys.executable, str(SCRIPTS / "arr_growth_gate.py"), "--queries", str(f),
                                "--today", TODAY.isoformat()], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["queries"][0]["account_domain"], "acme.example")

    def test_nonfinite_values_never_leak_into_json_output(self):
        def reject_constant(value):
            self.fail(f"nonstandard JSON constant {value}")
        for r in (row(current_arr_usd=float("inf"), observed_dates=0),
                  row(net_change_usd=float("nan")),
                  row(account={"name": float("nan"), "owner_id": "005OTHER"})):
            p = self.run_gate({"rows": [r]})
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertEqual(p.stderr, "")
            self.assertEqual(json.loads(p.stdout, parse_constant=reject_constant)["verdict"], "error")


if __name__ == "__main__":
    unittest.main()
