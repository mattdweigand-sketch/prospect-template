import _support
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SHARED = _support.SHARED
SCRIPTS = ROOT / "workflows" / "signal-outreach"
sys.path.insert(0, str(ROOT / "_shared" / "scripts"))
sys.path.insert(0, str(SCRIPTS))
import common  # noqa: E402
import outreach_gate as og  # noqa: E402

POLICY = common.load_policy(SHARED)
POL = POLICY["outreach"]
TT = common.load_talk_track(SHARED)
PT = timezone(timedelta(hours=-7))
NOW = datetime(2026, 9, 22, 14, 0, tzinfo=PT)


# Concise buyer-facing excerpts used in otherwise valid packet fixtures.
MESSAGE_LINE = "Example Offer helps teams plan and deliver reviewed operational projects."


PACKET = {
    "bundle": {"account_name": "Acme", "account_domain": "acme.example", "signal_type": "relevant_leader_appointment", "vertical": None,
               "published_date": "2026-09-10", "checked_on": "2026-09-22", "checked_at": "2026-09-22T13:30:00-07:00",
               "classification": "active_initiative", "relevance": "relevant_to_offer", "fit_reason": "The evidenced initiative matches the configured offer and its stated limits.",
               "gate":"evidence_gate", "source_url":"https://acme.example/news", "date_basis":"published",
               "quote": "Acme has appointed Jane Doe as Chief Operating Officer to lead operations improvement."},
    "talk_track": {"angle": "Implementation support", "persona": "initiative_owner",
                   "pick_reason": "The new operations lead owns rollout decisions, making implementation support across teams relevant."},
    "recipient": {"email": "jane.doe@acme.example", "name": "Jane Doe", "source": "existing CRM contact with email",
                  "title": "Chief Operating Officer", "title_override": None, "contact_id": "003JANE"},
    "account": {"id":"001ACME", "domain":"acme.example", "owner_id":POLICY["identity"]["crm_user_id"], "owner_is_active":True, "open_deal_ids":[]},
    "reads": {name:{"complete":True,"query_reference":"synthetic:"+name,"checked_at":"2026-09-22T13:30:00-07:00","account_domain":"acme.example","recipient_email":"jane.doe@acme.example","window_start":"2026-08-23"} for name in ("tasks","events","email_sent")},
    "activity": [{"kind": "task", "subtype": "Email", "date": "2026-06-01", "status": "Completed", "subject": "old email"},
                 {"kind": "task", "subtype": "Task", "date": "2026-09-17", "status": "Completed", "subject": "LinkedIn - Connected"}],
    "draft": {"subject": "Chief Operating Officer, first quarter",
              "body": "You named Jane Doe Chief Operating Officer last week.\n\nThat usually creates a tooling review. "
                      + MESSAGE_LINE + "\n\nWorth a 20 minute call?"},
}


def pk(**changes):
    p = copy.deepcopy(PACKET)
    for k, v in changes.items():
        sect, key = k.split("__")
        p[sect][key] = v
    if "recipient__email" in changes:
        for receipt in p["reads"].values(): receipt["recipient_email"] = changes["recipient__email"]
    return p


def angle_packet(angle, signal_type, persona, title):
    return pk(bundle__signal_type=signal_type, talk_track__angle=angle,
              talk_track__persona=persona, recipient__title=title,
              draft__body="You named Jane Doe Chief Operating Officer.\n\n" + MESSAGE_LINE + "\n\nWorth a call?")


def shared_copy(mutate):
    """Copy the four files the gate reads into a temp dir, apply mutate(dir), return the Path. Caller removes it."""
    d = Path(tempfile.mkdtemp())
    for f in ("policy.yaml", "talk-track.md", "signals.md", "icp.md"):
        shutil.copy(SHARED / f, d / f)
    mutate(d)
    return d


def edit_meta(d, **fields):
    p = d / "talk-track.md"
    doc = common.markdown_document(p)
    for k, v in fields.items():
        if v is None: doc["meta"].pop(k, None)
        else: doc["meta"][k] = v
    p.write_text("---\n" + yaml.safe_dump(doc["meta"]) + "---\n\n" + doc["body"])


class OutreachGateTests(unittest.TestCase):
    def check(self, p, shared=SHARED, now=NOW):
        return og.check(p, POL, shared, now)

    def flags(self, p, shared=SHARED):
        return og.fit_flags(p, POL, shared)

    def assertBlocks(self, p, fragment, shared=SHARED, now=NOW):
        r = self.check(p, shared, now)
        self.assertTrue(any(fragment in x for x in r), f"{fragment!r} not in {r}")

    def test_clean_packet_allows(self):
        self.assertEqual(self.check(PACKET), [])
        self.assertEqual(self.flags(PACKET), [])

    # check 1
    def test_unknown_signal_type_blocks(self):
        self.assertBlocks(pk(bundle__signal_type="generic_marketing"), "bundle signal_type not a tier1 or tier2")

    # check 2
    def test_any_web_date_basis_passes(self):
        for basis in ("published", "page_event", "linkedin_post_id"):
            self.assertEqual(self.check(pk(bundle__date_basis=basis, bundle__gate="evidence_gate")), [], basis)

    def test_published_date_freshness_is_per_signal_type(self):
        self.assertEqual(self.check(pk(bundle__published_date="2026-06-24")), [])  # 90 days, relevant_leader_appointment allows 90
        self.assertBlocks(pk(bundle__published_date="2026-06-23"), "91 days old, relevant_leader_appointment freshness is 90 days")
        p = angle_packet("Workflow cost", "announced_initiative", "economic_buyer", "COO")
        p["bundle"]["published_date"] = "2026-07-24"  # 60 days
        self.assertEqual(self.check(p), [])
        p["bundle"]["published_date"] = "2026-07-23"  # 61 days
        self.assertBlocks(p, "61 days old, announced_initiative freshness is 60 days")

    # check 3
    def test_checked_at_elapsed_boundary(self):
        ok = (NOW - timedelta(hours=23, minutes=59)).isoformat()
        self.assertEqual(self.check(pk(bundle__checked_at=ok)), [])
        stale = (NOW - timedelta(hours=24, minutes=1)).isoformat()
        self.assertBlocks(pk(bundle__checked_at=stale), "checked_at older than policy")

    def test_checked_at_offset_is_honored(self):
        utc = (NOW - timedelta(hours=23, minutes=30)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        self.assertEqual(self.check(pk(bundle__checked_at=utc)), [])

    def test_date_only_or_naive_checked_at_blocks(self):
        p = pk(bundle__checked_on="2026-09-22"); del p["bundle"]["checked_at"]
        self.assertBlocks(p, "needs an ISO timestamp with a timezone offset")
        self.assertBlocks(pk(bundle__checked_at="2026-09-22T13:30:00"), "needs an ISO timestamp with a timezone offset")

    def test_future_read_and_publication_block_independently(self):
        self.assertBlocks(pk(bundle__checked_at="2099-01-01T12:00:00-08:00"), "checked_at is in the future")
        self.assertBlocks(pk(bundle__published_date="2099-01-01"), "published_date is in the future")

    def test_publication_date_preserves_utc_rollover_allowance(self):
        late = datetime.fromisoformat("2026-09-22T20:00:00-07:00")
        self.assertEqual(self.check(pk(bundle__published_date="2026-09-23"), now=late), [])
        self.assertBlocks(pk(bundle__published_date="2026-09-24"), "published_date is in the future", now=late)
        self.assertEqual(self.check(pk(bundle__published_date="2026-09-23"), now=late.astimezone(timezone.utc)), [])

    def test_invalid_publication_dates_are_unusable(self):
        for value in ("2026-09-22garbage", "2026-09-22T12:00:00Z", "2026-02-30", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(pk(bundle__published_date=value))

    def test_checked_on_with_offset_is_accepted_when_checked_at_missing(self):
        p = pk(bundle__checked_on="2026-09-22T13:30:00-07:00"); del p["bundle"]["checked_at"]
        self.assertEqual(self.check(p), [])

    # check 4


    def test_missing_pick_reason_blocks(self):
        self.assertBlocks(pk(talk_track__pick_reason=""), "talk_track.pick_reason must be a nonempty")
        self.assertBlocks(pk(talk_track__pick_reason=None), "talk_track.pick_reason must be a nonempty")

    def test_plain_language_judgment_and_unlisted_title_allow(self):
        p = pk(recipient__title="Implementation Program Lead", talk_track__persona="Owns delivery of the implementation project",
               talk_track__angle="A common platform across teams")
        self.assertEqual(self.check(p), [])

    def test_missing_judgment_or_responsibility_blocks(self):
        for field in ("angle", "persona", "pick_reason"):
            self.assertBlocks(pk(**{f"talk_track__{field}": " "}), f"talk_track.{field}")
        self.assertBlocks(pk(recipient__title=None), "verified responsibility must be stated")

    def test_discovery_and_legacy_bundles_do_not_enter_outreach(self):
        for value in (None, "early_indication", "general_mention"):
            self.assertBlocks(pk(bundle__classification=value), "active_initiative")
        for value in (None, "outside_offer", "unclear"):
            self.assertBlocks(pk(bundle__relevance=value), "relevant_to_offer")

    # check 5
    def test_review_by_in_the_past_blocks(self):
        d = shared_copy(lambda d: edit_meta(d, review_by="2026-09-21"))
        try:
            self.assertBlocks(PACKET, "meta.review_by 2026-09-21 is past", shared=d)
            edit_meta(d, review_by="2026-09-22")
            self.assertEqual(self.check(PACKET, shared=d), [])  # today is not past
        finally:
            shutil.rmtree(d)

    def test_review_by_uses_policy_clock(self):
        d = shared_copy(lambda d: edit_meta(d, review_by="2026-09-22"))
        try:
            self.assertEqual(self.check(PACKET, shared=d), [])
            self.assertBlocks(PACKET, "meta.review_by 2026-09-22 is past", shared=d, now=NOW + timedelta(days=1))
        finally:
            shutil.rmtree(d)

    def test_missing_review_by_blocks(self):
        d = shared_copy(lambda d: edit_meta(d, review_by=None))
        try:
            self.assertBlocks(PACKET, "meta.review_by missing", shared=d)
        finally:
            shutil.rmtree(d)

    def test_live_copy_is_in_review(self):
        self.assertTrue(TT["meta"]["review_by"])
        on_review_day = datetime.fromisoformat(str(TT["meta"]["review_by"]) + "T12:00:00-07:00")
        p = pk(bundle__checked_at=(on_review_day - timedelta(hours=1)).isoformat(),
               bundle__published_date=(on_review_day - timedelta(days=1)).date().isoformat())
        for receipt in p["reads"].values():
            receipt["checked_at"] = (on_review_day - timedelta(hours=1)).isoformat()
        self.assertEqual(self.check(p, now=on_review_day), [])

    # check 6


    def test_recipient_domain_mismatch_blocks_and_subdomain_allows(self):
        self.assertIn("recipient domain does not match bundle account_domain", self.check(pk(recipient__email="jane@email.com")))
        self.assertEqual(self.check(pk(recipient__email="jane@corp.acme.example")), [])

    def test_unverified_recipient_source_blocks(self):
        self.assertBlocks(pk(recipient__source="guessed from name pattern"), "recipient source not in policy")

    def test_directly_supplied_recipient_preserves_other_boundaries(self):
        p = pk(recipient__source="User supplied in this conversation", recipient__contact_id=None)
        self.assertEqual(self.check(p), [])
        p["recipient"]["email"] = "jane@other.example"
        self.assertBlocks(p, "recipient domain does not match")

    def test_crm_recipient_requires_contact_id(self):
        for value in (None, "", "  ", False, 12):
            self.assertBlocks(pk(recipient__contact_id=value), "needs a nonempty contact_id")
        p = pk()
        del p["recipient"]["contact_id"]
        self.assertBlocks(p, "needs a nonempty contact_id")

    def test_unusable_identity_fields_block(self):
        for value in (None, "", "  "):
            self.assertBlocks(pk(bundle__account_name=value), "account_name must be a nonempty string")
        for value in (None, "", "https://acme.example", "acme.example/path", "@acme.example", "com"):
            self.assertBlocks(pk(bundle__account_domain=value), "account_domain must be a usable domain")
        for value in (None, "", "acme.example", "jane@@acme.example", "jane doe@acme.example"):
            self.assertBlocks(pk(recipient__email=value), "email must be a usable address")

    # check 7
    def test_suppression_rules(self):
        cases = [({"kind": "task", "subtype": "Email", "date": "2026-09-05", "status": "Completed", "subject": "Email: intro"}, True),
                 ({"kind": "task", "subtype": "Call", "date": "2026-09-05", "status": "Not Started", "subject": "Call"}, False),
                 ({"kind": "task", "subtype": "Call", "date": "2026-09-12", "status": "Completed", "subject": "Call"}, True),
                 ({"kind": "event", "subtype": None, "date": "2026-09-12", "status": None, "subject": "Meeting"}, True),
                 ({"kind": "email_sent", "date": "2026-09-15", "status": None, "subject": "Hello"}, True)]
        for a, suppressed in cases:
            p = pk(); p["activity"].append(a)
            self.assertEqual(any(x.startswith("suppressed") for x in self.check(p)), suppressed, a)

    def test_suppression_is_per_contact(self):
        row = {"kind": "task", "subtype": "Email", "date": "2026-09-15", "status": "Completed", "subject": "Email: intro"}
        other = dict(row, who="003OTHERPERSON", who_kind="contact_id")
        same_id = dict(row, who="003JANE", who_kind="contact_id")
        same_email = dict(row, who="Jane.Doe@acme.example", who_kind="email")
        unknown = dict(row, who=None)
        for a, suppressed in ((other, False), (same_id, True), (same_email, True), (unknown, True)):
            p = pk(); p["recipient"]["contact_id"] = "003JANE"; p["activity"].append(a)
            self.assertEqual(any(x.startswith("suppressed") for x in self.check(p)), suppressed, a)
        p = pk(); p["activity"].append(dict(row, kind="email_sent", subtype=None, who="someone.else@acme.example", who_kind="email"))
        self.assertFalse(any(x.startswith("suppressed") for x in self.check(p)))

    def test_empty_targets_are_unknown_and_suppress(self):
        for who in (None, "", "  "):
            p = pk()
            p["activity"] = [{"kind": "task", "subtype": "Email", "status": "Completed", "date": "2026-09-22", "who": who}]
            self.assertBlocks(p, "suppressed:")

    def test_malformed_activity_never_looks_like_no_activity(self):
        cases = [None, {}, [None], [{"kind": "unknown", "date": "2026-09-22"}],
                 [{"kind": "event", "date": "bad"}], [{"kind": "event", "date": "2026-09-22", "who": []}],
                 [{"kind": "event", "date": "2026-09-22", "who": "unknown"}],
                 [{"kind": "event", "date": "2026-09-22", "who": "jane@acme.example,bob@acme.example"}],
                 [{"kind": "task", "date": "2026-09-22", "status": None, "subtype": "Email"}],
                 [{"kind": "task", "date": "2026-09-22", "status": "Completed", "subtype": None}]]
        for activity in cases:
            p = pk()
            p["activity"] = activity
            with self.subTest(activity=activity), self.assertRaises(ValueError):
                self.check(p)

    def test_blank_drafts_are_unusable_after_style_checks_removed(self):
        for field in ("subject", "body"):
            with self.assertRaises(ValueError):
                self.check(pk(**{f"draft__{field}": "  "}))

    def test_approved_q7_sentence_is_not_rejected_as_evidence_overlap(self):
        p = pk(talk_track__angle="Research infrastructure",
               draft__body="Example Offer does not make purchasing decisions on the buyer's behalf.\n\nWorth a call?")
        self.assertEqual(self.check(p), [])

    def test_style_and_lexical_similarity_are_not_hard_gates(self):
        p = pk(draft__subject="An intentionally longer subject that the external style linter may flag",
               draft__body="\n\n".join(["This is editorial wording for human review."] * 5))
        self.assertEqual(self.check(p), [])

    # check 8
    def test_number_from_quote_allows_and_stray_blocks(self):
        p = pk(bundle__quote="Acme hired 40 operations specialists this quarter and named Jane Doe Chief Operating Officer.")
        p["draft"]["body"] = "You hired 40 operations specialists.\n\nThat creates a tooling decision. " + MESSAGE_LINE + "\n\nWorth a call?"
        self.assertEqual(self.check(p), [])
        p["draft"]["body"] = "You hired 40 operations specialists.\n\nSome teams see a 30 percent lift. " + MESSAGE_LINE + "\n\nWorth a call?"
        self.assertBlocks(p, "numbers in body not in the bundle quote: 30")

    def test_invite_minutes_exempt_only_as_invitation_in_question(self):
        base = "You named a Chief Operating Officer.\n\n" + MESSAGE_LINE + "\n\n"
        self.assertEqual(self.check(pk(draft__body=base + "Worth 20 minutes?")), [])
        self.assertEqual(self.check(pk(draft__body=base + "Would you have 20 minutes to discuss?\n\nthe seller\nExample Offer")), [])
        p = pk(draft__body="You named a Chief Operating Officer.\n\nI have 20 minutes free this week. " + MESSAGE_LINE + "\n\nWorth a call?")
        self.assertBlocks(p, "numbers in body not in the bundle quote: 20")
        self.assertBlocks(pk(draft__body=base + "Worth 20 minutes, maybe 30?"), "the bundle quote: 30")

    def test_invite_minutes_do_not_authorize_same_number_elsewhere(self):
        p = pk(draft__body="You named a Chief Operating Officer.\n\nThis cuts costs by 20%. " + MESSAGE_LINE + "\n\nWould you have 20 minutes to discuss?")
        self.assertBlocks(p, "numbers in body not in the bundle quote: 20")

    def test_minutes_claim_in_question_still_blocks(self):
        base = "You named a Chief Operating Officer.\n\n" + MESSAGE_LINE + "\n\n"
        self.assertBlocks(pk(draft__body=base + "Could this save 20 minutes per report?"), "numbers in body not in the bundle quote: 20")
        self.assertBlocks(pk(draft__body=base + "Could this save you 20 minutes on each call?"), "numbers in body not in the bundle quote: 20")


    def test_allowed_names_pass(self):
        body = ("Hi Jane Doe,\n\nYou named Jane Doe Chief Operating Officer at Acme last week.\n\n"
                "Example Offer coordinates project work with the customer, who reviews the final deliverable.\n\n"
                "Worth a 20 minute call?\n\nBest,\nthe seller / Example Offer")
        self.assertEqual(self.check(pk(draft__body=body)), [])


    # flags


    def test_present_tense_capability_flags_c_when_verify_before_action(self):
        self.assertTrue(TT["meta"]["verify_before_action"])
        p = pk(draft__body="You named a Chief Operating Officer.\n\nExample Offer supports this project type. " + MESSAGE_LINE + "\n\nWorth a call?")
        self.assertEqual(self.check(p), [])
        self.assertEqual(self.flags(p), ["verify before action. Check current support for capability wording 'supports'"])
        d = shared_copy(lambda d: edit_meta(d, verify_before_action=False))
        try:
            self.assertEqual(self.flags(p, shared=d), [])
        finally:
            shutil.rmtree(d)

    def test_flags_never_block(self):
        p = pk(draft__body="Example Offer supports this workflow. Worth a call?")
        self.assertEqual(self.check(p), [])
        self.assertTrue(self.flags(p))

    def test_unknown_unit_or_signal_yields_no_crash_in_flags(self):
        self.assertEqual(self.flags(pk(talk_track__angle="nope")), [])
        self.assertEqual(self.flags(pk(bundle__signal_type="generic_marketing")), [])

    # clock and CLI
    def test_parse_now_uses_policy_timezone(self):
        t = og.parse_now("2026-09-22", POLICY)
        self.assertEqual((t.hour, t.tzinfo.key), (12, POLICY["identity"]["timezone"]))
        self.assertEqual(og.parse_now(None, POLICY).tzinfo.key, POLICY["identity"]["timezone"])
        self.assertEqual(og.parse_now("2026-09-22T20:00:00Z", POLICY).isoformat(), "2026-09-22T20:00:00+00:00")
        with self.assertRaises(ValueError):
            og.parse_now("2026-09-22T13:30:00", POLICY)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            def run(packet, now=NOW.isoformat()):
                f = Path(td) / "packet.json"
                f.write_text(json.dumps(packet))
                return subprocess.run([sys.executable, str(SCRIPTS / "outreach_gate.py"), "--packet", str(f), "--now", now],
                                      capture_output=True, text=True)
            p = run(PACKET)
            self.assertEqual(p.returncode, 0, p.stdout)
            out = json.loads(p.stdout)
            self.assertEqual(out["verdict"], "allow")
            self.assertEqual(out["flags"], [])
            self.assertEqual((out["angle"], out["persona"]), ("Implementation support", "initiative_owner"))
            self.assertNotIn("talk_track_id", out)
            p = run(pk(bundle__published_date="2026-01-01"))
            self.assertEqual(p.returncode, 1)
            self.assertIn("flags", json.loads(p.stdout))
            p = run({})
            self.assertEqual(p.returncode, 2)
            self.assertEqual(json.loads(p.stdout)["verdict"], "error")
            p = run(PACKET, now="2026-09-22T13:30:00")  # naive clock is unusable input, not a block
            self.assertEqual(p.returncode, 2, p.stdout)
            self.assertIn("timezone offset", json.loads(p.stdout)["reason"])


class WarehouseSourcedSignal(unittest.TestCase):
    """paid_individuals_present arrives as the signal-outreach wrapper around a privacy-checked signal-user-scan bundle."""

    ADOPTION = {
        "account_name": "Acme", "crm_account_id": "001A000000AAAAA", "account_domain": "acme.example",
        "data_through_date": "2026-09-21", "mapped_org_count": 1, "org_subscribed": False, "org_paying": False,
        "org_service_types": [], "org_platforms": [], "paid_individuals_exist": True, "adoption": "individuals_only",
    }

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.shared = Path(self.temp.name)
        for source in SHARED.iterdir():
            if source.is_file(): shutil.copyfile(source, self.shared / source.name)
        policy = yaml.safe_load((self.shared / "policy.yaml").read_text())
        policy["user_scan"]["enabled"] = True  # explicit synthetic module fixture
        (self.shared / "policy.yaml").write_text(yaml.safe_dump(policy))

    def check(self, p):
        return og.check(p, POL, self.shared, NOW)

    def test_disabled_subscription_module_blocks_warehouse_outreach(self):
        reasons = og.check(self.user_scan_packet(), POL, SHARED, NOW)
        self.assertTrue(any("adoption is disabled" in reason for reason in reasons))

    def user_scan_packet(self, adoption=None, **bundle_extra):
        ab = dict(self.ADOPTION, **(adoption or {}))
        p = pk(talk_track__angle="Team workflows", talk_track__persona="initiative_owner",
               talk_track__pick_reason="Verified individual use supports exploring a team workflow without assuming who paid or company sanction.",
               recipient__title="Head of Operations",
               draft__subject="Example Offer already in use at Acme",
               draft__body="Some of your team already pay for Example Offer themselves.\n\n"
                           + MESSAGE_LINE + "\n\n"
                           "Worth a 20 minute call?")
        p["bundle"] = {
            "signal_type": "paid_individuals_present", "published_date": ab["data_through_date"],
            "checked_at": "2026-09-22T13:30:00-07:00", "quote": POLICY["user_scan"]["statements"]["individuals_only"],
            "date_basis": "warehouse", "account_domain": ab["account_domain"], "account_name": ab["account_name"],
            "adoption_bundle": ab,
        }
        p["bundle"].update(bundle_extra)
        p["account"]["id"] = ab["crm_account_id"]
        return p

    def test_wrapped_user_scan_bundle_allows(self):
        p = self.user_scan_packet()
        self.assertEqual(self.check(p), [])
        self.assertEqual(og.fit_flags(p, POL, SHARED), [])

    def test_web_gate_bundle_blocks(self):
        reasons = self.check(self.user_scan_packet(gate="evidence_gate"))
        self.assertTrue(any("not the web" in x for x in reasons), reasons)

    def test_source_url_bundle_blocks(self):
        reasons = self.check(self.user_scan_packet(source_url="https://acme.example/news"))
        self.assertTrue(any("not the web" in x for x in reasons), reasons)

    def test_missing_adoption_bundle_blocks(self):
        p = self.user_scan_packet()
        del p["bundle"]["adoption_bundle"]
        reasons = self.check(p)
        self.assertTrue(any("needs adoption_bundle" in x for x in reasons), reasons)

    def test_adoption_bundle_privacy_problem_blocks(self):
        reasons = self.check(self.user_scan_packet(adoption={"user_emails": ["a@acme.example"]}))
        self.assertTrue(any("failed privacy_check" in x and "forbidden key: user_emails" in x for x in reasons), reasons)

    def test_adoption_not_individuals_only_blocks(self):
        reasons = self.check(self.user_scan_packet(adoption={"adoption": "org_adopted", "org_subscribed": True, "org_paying": True}))
        self.assertTrue(any("needs individuals_only" in x for x in reasons), reasons)

    def test_quote_must_equal_policy_statement(self):
        reasons = self.check(self.user_scan_packet(quote="Everyone at Acme uses Example Offer."))
        self.assertIn("bundle quote must equal user_scan.statements.individuals_only", reasons)

    def test_exact_adoption_statement_in_body_allows(self):
        p = self.user_scan_packet()
        p["draft"]["body"] = POLICY["user_scan"]["statements"]["individuals_only"] + "\n\n" + p["draft"]["body"].split("\n\n", 1)[1]
        self.assertEqual(self.check(p), [])

    def test_stale_data_through_date_blocks(self):
        reasons = self.check(self.user_scan_packet(adoption={"data_through_date": "2026-09-20"}))
        self.assertTrue(any("2 days old, paid_individuals_present freshness is 1 days" in x for x in reasons), reasons)

    def test_wrapper_cannot_reassign_or_redate_embedded_adoption(self):
        for key, value in (("account_name", "Other Company"), ("account_domain", "other.example"),
                           ("data_through_date", "2020-01-01")):
            p = self.user_scan_packet()
            p["bundle"]["adoption_bundle"][key] = value
            self.assertTrue(any(f"must match adoption_bundle {key}" in x for x in self.check(p)), key)

    def test_warehouse_identity_cannot_be_blank(self):
        for key in ("account_name", "account_domain", "crm_account_id", "data_through_date"):
            p = self.user_scan_packet()
            p["bundle"]["adoption_bundle"][key] = ""
            self.assertTrue(any(f"adoption_bundle {key} must be a nonempty string" in x for x in self.check(p)), key)

    def test_web_type_with_evidence_gate_mark_not_blocked_on_source(self):
        reasons = self.check(pk(bundle__gate="evidence_gate"))
        self.assertFalse(any("not the web" in x for x in reasons), reasons)
        self.assertFalse(any("adoption_bundle" in x for x in reasons), reasons)


if __name__ == "__main__":
    unittest.main()
