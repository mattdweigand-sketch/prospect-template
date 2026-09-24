"""Synthetic regression tests; no live services."""
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


from gate_fixtures import SCRIPTS, SHARED
sys.path.insert(0, str(SCRIPTS))
import approval  # noqa: E402
import factory
import outreach_gate as og  # noqa: E402

POL = json.loads((SHARED / "policy.json").read_text())["outreach"]
ROWS = {r["id"]: r for r in json.loads((SHARED / "claims.json").read_text())["claims"]}
PT = timezone(timedelta(hours=-7))
NOW = datetime(2026, 9, 22, 14, 0, tzinfo=PT)
PACKET = {
    "activity_complete": True, "voice_anchor_reference": "synthetic-approved-email",
    "bundle": {"gate": "evidence_gate", "account_name": "Acme", "account_domain": "example.org", "signal_type": "operations_leader_appointment", "vertical": None,
               "published_date": "2026-09-10", "checked_on": "2026-09-22", "checked_at": "2026-09-22T13:30:00-07:00",
               "quote": "Acme has appointed Jane Doe as Chief Operating Officer to lead business operations."},
    "claim": {"id": "report_setup", "evidence": ROWS["report_setup"]["evidence"], "persona": "operations_owner",
              "pick_reason": "The quote names a new business operations lead whose tooling review can assess the claim's report export capability."},
    "recipient": {"email": "jane.doe@example.org", "name": "Jane Doe", "source": "existing CRM Contact",
                  "title": "Chief Operating Officer", "title_override": None},
    "activity": [{"kind": "task", "subtype": "Email", "date": "2026-06-01", "status": "Completed", "subject": "old email"},
                 {"kind": "task", "subtype": "Task", "date": "2026-09-17", "status": "Completed", "subject": "LinkedIn - Connected"}],
    "draft": {"subject": "Chief Operating Officer, first quarter",
              "body": "You named Jane Doe Chief Operating Officer last week.\n\nThat usually creates a tooling review. Access alone rarely drives use, so plan for repetition and visible examples early.\n\nWorth a 20 minute call?"},
}


def pk(**changes):
    p = copy.deepcopy(PACKET)
    for k, v in changes.items():
        sect, key = k.split("__")
        p[sect][key] = v
    return p


def row_packet(rid, signal_type, vertical=None, persona=None, title=None):
    r = ROWS[rid]
    return pk(bundle__signal_type=signal_type, bundle__vertical=vertical, claim__id=rid, claim__evidence=r["evidence"],
              claim__persona=persona or r["personas"][0], recipient__title=title or "Head of Operations")


def shared_copy(mutate):
    """Copy the four files the gate reads into a temp dir, apply mutate(dir), return the Path. Caller removes it."""
    d = Path(tempfile.mkdtemp())
    for f in ("policy.json", "claims.json", "taxonomy.json", "icp.md"):
        shutil.copy(SHARED / f, d / f)
    mutate(d)
    return d


def edit_row(d, rid, restamp=False, **fields):
    p = d / "claims.json"
    tt = json.loads(p.read_text())
    for r in tt["claims"]:
        if r["id"] == rid:
            r.update(fields)
            if restamp:
                r.pop("approved", None)
                r["approved"] = approval.make_stamp(r, "2026-09-22")
    p.write_text(json.dumps(tt, indent=2))


def edit_signal(d, sid, **fields):
    p = d / "taxonomy.json"
    t = json.loads(p.read_text())
    for s in t["signals"]:
        if s["id"] == sid:
            s.update(fields)
    p.write_text(json.dumps(t, indent=2))


def edit_persona_cares(d):
    p = d / "icp.md"
    s = p.read_text().replace("Decides how teams review repeatable work.", "Decides something else.", 1)
    p.write_text(s)


class OutreachGateTests(unittest.TestCase):
    def check(self, p, shared=SHARED, now=NOW):
        return og.check(p, POL, shared, now)

    def assertBlocks(self, p, fragment, shared=SHARED, now=NOW):
        r = self.check(p, shared, now)
        self.assertTrue(any(fragment in x for x in r), f"{fragment!r} not in {r}")

    def test_clean_packet_allows(self):
        self.assertEqual(self.check(PACKET), [])

    def test_provider_task_statuses_use_explicit_mapping(self):
        policy = copy.deepcopy(POL)
        policy["task_status_map"] = {"Done": "completed", "Fertig": "completed", "Queued": "open", "Abandoned": "cancelled"}
        packet = pk()
        for native, suppressed in (("Done", True), ("Fertig", True), ("Queued", False), ("Abandoned", False)):
            with self.subTest(status=native):
                packet["activity"] = [{"kind": "task", "status": native, "subtype": "Email", "date": NOW.date().isoformat()}]
                reasons = og.check(packet, policy, SHARED, NOW)
                self.assertEqual(any("suppressed:" in reason for reason in reasons), suppressed)

    def test_unknown_missing_or_invalid_status_mapping_stops_check(self):
        packet = pk()
        policy = copy.deepcopy(POL)
        policy["task_status_map"] = {"Done": "completed"}
        for status in ("Completed", "unknown", "", None, True, []):
            packet["activity"] = [{"kind": "task", "status": status, "subtype": "Email", "date": NOW.date().isoformat()}]
            with self.subTest(status=status), self.assertRaises(ValueError):
                og.check(packet, policy, SHARED, NOW)
        packet["activity"][0]["status"] = "Done"
        for mapping in ({}, None, {"Done": "probably"}, {"Done": False}):
            policy["task_status_map"] = mapping
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                og.check(packet, policy, SHARED, NOW)

    def test_private_signal_cannot_replace_public_outreach_evidence(self):
        packet = pk(bundle__signal_type="paid_individuals_present", bundle__published_date=NOW.date().isoformat())
        self.assertBlocks(packet, "bundle signal_type must use a web source")

    def test_unconfigured_source_blocks_even_with_current_signal_stamp(self):
        for source in (None, "", "warehouse"):
            d = shared_copy(lambda d: None)
            try:
                tax = factory.read(d / "taxonomy.json")
                signal = next(s for s in tax["signals"] if s["id"] == "operations_leader_appointment")
                signal["source"] = source
                signal["approved"] = approval.make_stamp(signal, "2026-09-22")
                factory.write(d / "taxonomy.json", tax)
                with self.subTest(source=source):
                    self.assertEqual(self.check(PACKET, shared=d), ["bundle signal_type must use a web source"])
            finally:
                shutil.rmtree(d)

    # freshness
    def test_published_date_freshness_is_per_signal_type(self):
        self.assertEqual(self.check(pk(bundle__published_date="2026-06-24")), [])  # 90 days, operations_leader_appointment allows 90
        self.assertBlocks(pk(bundle__published_date="2026-06-23"), "91 days old, operations_leader_appointment freshness is 90 days")
        p = row_packet("scheduled_reports", "public_operations_initiative", persona="business_sponsor", title="COO")
        p["bundle"]["published_date"] = "2026-07-24"  # 60 days
        self.assertEqual(self.check(p), [])
        p["bundle"]["published_date"] = "2026-07-23"  # 61 days
        self.assertBlocks(p, "61 days old, public_operations_initiative freshness is 60 days")

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

    def test_checked_on_with_offset_is_accepted_when_checked_at_missing(self):
        p = pk(bundle__checked_on="2026-09-22T13:30:00-07:00"); del p["bundle"]["checked_at"]
        self.assertEqual(self.check(p), [])

    # row eligibility
    def test_claim_evidence_must_match_row(self):
        self.assertIn("claim evidence does not match the claims.json row", self.check(pk(claim__evidence="Access alone drives adoption")))

    def test_claim_evidence_tolerates_whitespace_and_case(self):
        self.assertEqual(self.check(pk(claim__evidence="export setup needs a  reviewer\nby default.")), [])

    def test_unknown_claim_id_blocks(self):
        self.assertBlocks(pk(claim__id="nope"), "claim id not in claims.json")

    def flags(self, p):
        return og.fit_flags(p, POL, SHARED)

    def test_unbound_claim_flags_binding_independently_of_vertical(self):
        p = row_packet("data_exchange", "operations_leader_appointment", vertical="technology", persona="technical_evaluator", title="CIO")
        self.assertEqual(self.check(p), [])
        binding = "best guess. claim data_exchange is outside the operations_leader_appointment binding"
        self.assertEqual(self.flags(p), [binding])
        p = row_packet("data_exchange", "operations_leader_appointment", vertical="legal", persona="technical_evaluator", title="CIO")
        self.assertEqual(self.check(p), [])
        self.assertEqual(self.flags(p), [binding, "best guess. claim data_exchange verticals ['technology', 'financial_services', 'professional_services'] do not include bundle vertical 'legal'"])

    def test_bound_vertical_row_allows_when_vertical_and_persona_fit(self):
        p = row_packet("data_exchange", "supplier_partnership", vertical="technology", persona="technical_evaluator", title="CIO")
        self.assertEqual(self.check(p), [])
        self.assertEqual(self.flags(p), [])

    def test_bound_vertical_row_flags_not_blocks_when_vertical_differs(self):
        p = row_packet("data_exchange", "supplier_partnership", vertical="legal", persona="technical_evaluator", title="CIO")
        self.assertEqual(self.check(p), [])
        self.assertEqual(self.flags(p), ["best guess. claim data_exchange verticals ['technology', 'financial_services', 'professional_services'] do not include bundle vertical 'legal'"])

    def test_vertical_row_flags_when_bundle_vertical_is_null(self):
        p = row_packet("data_exchange", "supplier_partnership", vertical=None, persona="technical_evaluator", title="CIO")
        self.assertEqual(self.check(p), [])
        self.assertTrue(any("do not include bundle vertical None" in x for x in self.flags(p)))

    def test_persona_outside_row_flags_not_blocks(self):
        p = pk(claim__persona="champion")
        self.assertEqual(self.check(p), [])
        self.assertEqual(self.flags(p), ["best guess. claim report_setup personas do not include champion"])

    def test_unknown_row_yields_no_flags(self):
        self.assertEqual(self.flags(pk(claim__id="nope")), [])

    def test_unknown_persona_blocks(self):
        self.assertBlocks(pk(claim__persona="cfo"), "not an icp.md persona id")

    def test_missing_pick_reason_blocks(self):
        missing = pk()
        missing["claim"].pop("pick_reason")
        self.assertBlocks(missing, "claim.pick_reason missing")
        for value in ("", " \t\n", None, False, 1, [], {}):
            with self.subTest(value=value):
                self.assertBlocks(pk(claim__pick_reason=value), "claim.pick_reason missing")

    def test_held_row_blocks(self):
        d = shared_copy(lambda d: None)
        p = d / "claims.json"; tt = json.loads(p.read_text()); tt["held"] = ["report_setup"]
        p.write_text(json.dumps(tt, indent=2))
        try:
            self.assertBlocks(PACKET, "claim report_setup is held in claims.json held", shared=d)
        finally:
            shutil.rmtree(d)

    def test_unknown_signal_type_blocks(self):
        self.assertBlocks(pk(bundle__signal_type="generic_marketing"), "bundle signal_type not a tier1 or tier2")

    # approval stamps
    def test_fixture_units_are_all_stamped(self):
        for r in ROWS.values():
            self.assertTrue(approval.stamp_current(r, r.get("approved")), r["id"])
        t = json.loads((SHARED / "taxonomy.json").read_text())
        for s in t["signals"]:
            self.assertTrue(approval.stamp_current(s, s.get("approved")), s["id"])
        fm = factory.frontmatter(SHARED)
        self.assertTrue(approval.stamp_current(fm["persona_cares"], fm["persona_cares_approved"]))

    def test_changed_row_blocks_until_restamped(self):
        d = shared_copy(lambda d: edit_row(d, "report_setup", track="A new sentence nobody approved."))
        try:
            self.assertBlocks(PACKET, "claim report_setup changed since its approval stamp", shared=d)
            edit_row(d, "report_setup", restamp=True)
            self.assertEqual(self.check(PACKET, shared=d), [])
        finally:
            shutil.rmtree(d)

    def test_changed_signal_entry_blocks(self):
        d = shared_copy(lambda d: edit_signal(d, "operations_leader_appointment", freshness_days=365))
        try:
            self.assertBlocks(PACKET, "signal type operations_leader_appointment changed since its approval stamp", shared=d)
        finally:
            shutil.rmtree(d)

    def test_changed_persona_cares_blocks(self):
        d = shared_copy(edit_persona_cares)
        try:
            self.assertBlocks(PACKET, "icp.md persona_cares changed since its approval stamp", shared=d)
        finally:
            shutil.rmtree(d)

    # numbers
    def test_number_from_claim_or_quote_allows(self):
        p = row_packet("access_controls", "service_procurement", persona="technical_evaluator", title="CIO")
        p["draft"]["body"] = "Your RFP names admin controls.\n\nThe 2026 release notes cover credit controls and Teams. Happy to walk through them.\n\nWorth a call?"
        self.assertEqual(self.check(p), [])
        p = pk(bundle__quote="Acme hired 40 operations engineers this quarter.")
        p["draft"]["body"] = "You hired 40 operations engineers.\n\nThat creates a tooling decision. Access alone rarely drives use.\n\nWorth a call?"
        self.assertEqual(self.check(p), [])

    def test_number_only_in_limit_blocks(self):
        d = shared_copy(lambda d: edit_row(d, "report_setup", restamp=True, limit="Do not claim a 30 percent lift."))
        try:
            p = pk(draft__body="You named a Chief Operating Officer.\n\nSome teams see a 30 percent lift.\n\nWorth a call?")
            self.assertBlocks(p, "numbers in body not in the row's claim or track or the bundle quote: 30", shared=d)
        finally:
            shutil.rmtree(d)

    def test_invite_minutes_exempt_only_as_invitation_in_question(self):
        self.assertEqual(self.check(pk(draft__body="You named a Chief Operating Officer.\n\nAccess alone rarely drives use.\n\nWorth 20 minutes?")), [])
        self.assertEqual(self.check(pk(draft__body="You named a Chief Operating Officer.\n\nAccess alone rarely drives use.\n\nWould you have 20 minutes to discuss?\n\nSeller\nExample Product")), [])
        p = pk(draft__body="You named a Chief Operating Officer.\n\nI have 20 minutes free this week. Access alone rarely drives use.\n\nWorth a call?")
        self.assertBlocks(p, "numbers in body not in the row's claim or track or the bundle quote: 20")
        p = pk(draft__body="You named a Chief Operating Officer.\n\nAccess alone rarely drives use.\n\nWorth 20 minutes, maybe 30?")
        self.assertBlocks(p, "the bundle quote: 30")

    def test_invite_minutes_do_not_authorize_same_number_elsewhere(self):
        p = pk(draft__body="You named a Chief Operating Officer.\n\nThis cuts costs by 20%. Access alone rarely drives use.\n\nWould you have 20 minutes to discuss?")
        self.assertBlocks(p, "numbers in body not in the row's claim or track or the bundle quote: 20")

    def test_minutes_claim_in_question_still_blocks(self):
        p = pk(draft__body="You named a Chief Operating Officer.\n\nAccess alone rarely drives use.\n\nCould this save 20 minutes per report?")
        self.assertBlocks(p, "numbers in body not in the row's claim or track or the bundle quote: 20")
        p = pk(draft__body="You named a Chief Operating Officer.\n\nAccess alone rarely drives use.\n\nCould this save you 20 minutes on each call?")
        self.assertBlocks(p, "numbers in body not in the row's claim or track or the bundle quote: 20")

    # proof names
    def test_proof_name_blocks_when_external_ok_false(self):
        p = row_packet("private_case_study", "incumbent_standardization", persona="economic_buyer", title="CIO")
        p["draft"]["body"] = "You standardized on Example Tool.\n\nExample Private Customer found the same gap.\n\nWorth a call?"
        self.assertBlocks(p, "body names Example Private Customer from row private_case_study proof")

    def test_proof_name_allowed_for_chosen_row_with_external_ok(self):
        p = row_packet("public_case_study", "operations_leader_appointment", vertical="legal", persona="business_sponsor", title="CIO")
        p["draft"]["body"] = "You named a Chief Operating Officer.\n\nExample Public Customer says cited context matters because attorneys can check it.\n\nWorth a call?"
        self.assertEqual(self.check(p), [])

    def test_prospect_name_equal_to_a_proof_name_passes(self):
        p = row_packet("report_delivery", "operations_leader_appointment", persona="operations_owner")
        p["bundle"]["account_name"] = "Example Prospect"
        p["bundle"]["account_domain"] = "example.org"
        p["recipient"]["email"] = "jane@example.org"
        p["draft"]["body"] = "You named a Chief Operating Officer at Example Prospect.\n\nThat creates a tooling review. Customers describe getting back finished work.\n\nWorth a call?"
        self.assertEqual(self.check(p), [])
        p["bundle"]["account_name"] = "Example Prospect Oyj"
        self.assertBlocks(p, "body names Example Prospect from row policy_updates proof")

    def test_proof_name_from_another_row_blocks(self):
        p = pk(draft__body="You named a Chief Operating Officer.\n\nExample Public Customer says cited context matters.\n\nWorth a call?")
        self.assertBlocks(p, "body names Example Public Customer from row public_case_study proof")

    # evidence copying
    def test_eight_word_evidence_run_blocks_and_seven_passes(self):
        ev = ROWS["report_delivery"]["evidence"]
        words = re.findall(r"[a-z0-9&'-]+", ev.lower())
        p = row_packet("report_delivery", "operations_leader_appointment", persona="operations_owner")
        p["draft"]["body"] = "You named a Chief Operating Officer.\n\n" + " ".join(words[:8]) + ".\n\nWorth a call?"
        self.assertBlocks(p, "copies 8 or more words from the row's evidence")
        p["draft"]["body"] = "You named a Chief Operating Officer.\n\n" + " ".join(words[:7]) + ".\n\nWorth a call?"
        self.assertEqual(self.check(p), [])

    # recipient
    def test_recipient_title_outside_targets_blocks(self):
        self.assertBlocks(pk(recipient__title="VP of Marketing"), "outside target_titles")

    def test_recipient_title_substring_match_allows(self):
        self.assertEqual(self.check(pk(recipient__title="Global Head of Operations and Data")), [])

    def test_title_aliases_match_complete_phrases_only(self):
        for title in ("Payroll Coordinator", "IT Procurement Coordinator", "Chief", "C"):
            with self.subTest(title=title):
                self.assertBlocks(pk(recipient__title=title), "outside target_titles")
        self.assertEqual(self.check(pk(recipient__title="Regional COO, Business Services")), [])

    def test_quoted_executive_matches_evidence_subject(self):
        p = row_packet("report_delivery", "executive_statements", persona="economic_buyer", title="Chief Knowledge Officer")
        p["bundle"]["evidence_subject"] = "Jane Doe"
        self.assertEqual(self.check(p), [])
        p["recipient"]["name"] = "John Roe"
        self.assertBlocks(p, "outside target_titles")

    def test_title_override_allows_and_blank_does_not(self):
        p = pk(recipient__title="VP of Marketing", recipient__title_override="Seller named her in the thread, she owns the operations budget")
        self.assertEqual(self.check(p), [])
        self.assertBlocks(pk(recipient__title="VP of Marketing", recipient__title_override="  "), "outside target_titles")

    def test_recipient_domain_mismatch_blocks_and_subdomain_allows(self):
        self.assertIn("recipient domain does not match bundle account_domain", self.check(pk(recipient__email="jane@example.net")))
        self.assertEqual(self.check(pk(recipient__email="jane@corp.example.org")), [])

    def test_unverified_recipient_source_blocks(self):
        self.assertBlocks(pk(recipient__source="guessed from name pattern"), "recipient source not in policy")

    # suppression
    def test_suppression_rules(self):
        cases = [({"kind": "task", "subtype": "Email", "date": "2026-09-05", "status": "Completed", "subject": "Email: intro"}, True),
                 ({"kind": "task", "subtype": "Call", "date": "2026-09-05", "status": "Not Started", "subject": "Call"}, False),
                 ({"kind": "task", "subtype": "Call", "date": "2026-09-12", "status": "Completed", "subject": "Call"}, True),
                 ({"kind": "event", "subtype": None, "date": "2026-09-12", "status": None, "subject": "Meeting"}, True),
                 ({"kind": "mail_sent", "date": "2026-09-15", "status": None, "subject": "Hello"}, True)]
        for a, suppressed in cases:
            p = pk(); p["activity"].append(a)
            self.assertEqual(any(x.startswith("suppressed") for x in self.check(p)), suppressed, a)

    # draft shape
    def test_quote_dump_blocks(self):
        self.assertIn("signal quote pasted whole into body", self.check(pk(draft__body=PACKET["bundle"]["quote"] + "\n\nWorth a call?")))

    def test_date_opener_blocks(self):
        self.assertIn("body opens on a date", self.check(pk(draft__body="On September 10, Acme named a Chief Operating Officer.\n\nWorth a call?")))

    def test_two_questions_block(self):
        self.assertBlocks(pk(draft__body="You named a Chief Operating Officer.\n\nHow is it going? Worth a call?"), "question marks")

    def test_long_subject_blocks(self):
        self.assertIn("subject too long", self.check(pk(draft__subject="a b c d e f g h i j")))

    def test_subject_uses_claim_proof_and_surface_checks(self):
        for subject, reason in (("Costs fall 999%", "numbers in subject"),
                                ("Worth 20 minutes", "numbers in subject"),
                                ("Example Private Customer", "subject names Example Private Customer"),
                                ("**Great news** 🎉", "subject:"),
                                ("A seamless review", "subject: forbidden phrase")):
            with self.subTest(subject=subject):
                self.assertBlocks(pk(draft__subject=subject), reason)
        policy = copy.deepcopy(POL)
        policy["lint"]["max_body_words"] = 2
        p = pk(draft__subject="A longer but allowed subject", draft__body="Discuss exports?")
        self.assertEqual(og.check(p, policy, SHARED, NOW), [])

    def test_repeated_selected_proof_name_remains_allowed(self):
        d = shared_copy(lambda d: edit_row(d, "private_case_study", restamp=True,
                                          proof={"name": "Example Public Customer", "external_ok": True}))
        try:
            p = row_packet("public_case_study", "operations_leader_appointment", persona="business_sponsor", title="CIO")
            p["draft"]["body"] = "You named a Chief Operating Officer.\n\nExample Public Customer described its report review.\n\nWorth a call?"
            self.assertEqual(self.check(p, shared=d), [])
            edit_row(d, "public_case_study", restamp=True, proof={"name": "Example Public Customer", "external_ok": False})
            self.assertBlocks(p, "body names Example Public Customer", shared=d)
        finally:
            shutil.rmtree(d)

    def test_nonactionable_adoption_never_authorizes_a_sentence(self):
        d = shared_copy(lambda d: None)
        try:
            policy = factory.read(d / "policy.json")
            policy["adoption"].update(enabled=True, approved_statements={"org_adopted": "An organization subscription is present."})
            factory.write(d / "policy.json", policy)
            for category in ("none_found", "unknown"):
                p = pk()
                sentence = "Your team is adopting the service."
                p.update(adoption_sentence=sentence, adoption_review_reference="synthetic-review", adoption_checked_at=NOW.isoformat(),
                         adoption_bundle={"account_name": "Acme", "account_id": "account-1", "account_domain": "example.org",
                                          "data_through_date": "2026-09-21", "mapped_org_count": 0, "org_subscribed": False,
                                          "org_paying": False, "org_service_types": [], "org_platforms": [],
                                          "paid_individuals_exist": False, "adoption": category, "source_reference": "synthetic-aggregate"})
                p["draft"]["body"] += "\n\n" + sentence
                with self.subTest(category=category):
                    self.assertBlocks(p, "adoption sentence must equal", shared=d)
                    policy["adoption"]["approved_statements"][category] = sentence
                    factory.write(d / "policy.json", policy)
                    with self.assertRaises(ValueError):
                        self.check(p, shared=d)
                    del policy["adoption"]["approved_statements"][category]
                    factory.write(d / "policy.json", policy)
        finally:
            shutil.rmtree(d)

    def test_malformed_packet_fields_and_config_are_unusable(self):
        for section in ("bundle", "claim", "recipient", "draft", "activity"):
            p = pk()
            p[section] = None
            with self.subTest(section=section), self.assertRaises(ValueError):
                self.check(p)
        for address in ("bad", "a@example.org,bob", ".a@example.org", "a..b@example.org"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.check(pk(recipient__email=address))
        policy = copy.deepcopy(POL)
        del policy["lint"]["no_markdown"]
        with self.assertRaises(ValueError):
            og.check(PACKET, policy, SHARED, NOW)

    def test_email_domain_comparison_is_canonical_without_mutating_recipient(self):
        p = pk(recipient__email="Jane@EXAMPLE.ORG.")
        self.assertEqual(self.check(p), [])
        self.assertEqual(p["recipient"]["email"], "Jane@EXAMPLE.ORG.")

    def test_cli_exit_codes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=SHARED) as f:
            json.dump(PACKET, f)
        cmd = [sys.executable, str(SCRIPTS / "outreach_gate.py"), "--packet", f.name, "--now", NOW.isoformat(), "--shared", str(SHARED)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(json.loads(p.stdout)["verdict"], "allow")
        self.assertEqual(json.loads(p.stdout)["flags"], [])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=SHARED) as f:
            json.dump(pk(bundle__published_date="2026-01-01"), f)
        p = subprocess.run(cmd[:3] + [f.name] + cmd[4:], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn("flags", json.loads(p.stdout))
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=SHARED) as f:
            f.write("{}")
        p = subprocess.run(cmd[:3] + [f.name] + cmd[4:], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


class DraftLintTests(unittest.TestCase):
    def test_supported_markdown_and_emoji_forms(self):
        for text in ("Read [details](https://example.org)", "> Quotation", "_emphasis_", "Use `code`", "🇺🇸", "1️⃣"):
            with self.subTest(text=text):
                self.assertTrue(og.lint_draft.check(text, POL["lint"]))
        for text in ("https://example.org/a/_path_", "It's a useful question", "Bonjour équipe, 你好"):
            with self.subTest(text=text):
                self.assertEqual(og.lint_draft.check(text, POL["lint"]), [])

    def test_direct_lint_validates_rules(self):
        rules = copy.deepcopy(POL["lint"])
        del rules["no_emoji"]
        with self.assertRaises(ValueError):
            og.lint_draft.check("Hello", rules)


if __name__ == "__main__":
    unittest.main()
