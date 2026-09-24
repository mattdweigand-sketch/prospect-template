"""Approved synthetic units for local tests only; no deployment data or connectors."""
import atexit
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import approval
import factory

_TEMP = tempfile.TemporaryDirectory(prefix="prospect-fixture-")
atexit.register(_TEMP.cleanup)
SHARED = Path(_TEMP.name)


def make_shared(dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    pol = json.loads((ROOT / "_shared/policy.example.json").read_text())
    pol["identity"].update(owner_id="owner-1", timezone="America/Los_Angeles")
    pol["outreach"]["task_status_map"] = {"Completed": "completed", "Not Started": "open", "Cancelled": "cancelled"}
    pol["routing"]["house_owner_ids"] = ["house-1", "house-2"]
    pol["arr_growth"].update(enabled=True, email_template={
        "subject": "Reporting workflow", "greeting_person": "Hi {first_name},",
        "greeting_team": "Hi {account_name} team,", "body": "Would a reporting review be useful?\n\nBest,\nSeller"})
    factory.write(dest / "policy.json", pol)
    fm = {"territory": {"min_employees": 200, "max_employees": 5000},
          "verticals": [{"id": k, "rank": n} for n, k in enumerate(("professional_services", "technology", "legal", "financial_services"), 1)],
          "disqualifiers": {"hard": ["unsupported_service_requirement"], "recoverable": ["existing_solution_meets_need"]},
          "persona_cares": {k: "Decides how teams review repeatable work." for k in ("operations_owner", "business_sponsor", "technical_evaluator", "economic_buyer", "champion")}}
    fm["persona_cares_approved"] = approval.make_stamp(fm["persona_cares"], "2026-09-22")
    (dest / "icp.md").write_text("---\n" + json.dumps(fm, indent=2) + "\n---\n# Synthetic ICP\n")
    ids = ("report_setup", "scheduled_reports", "data_exchange", "access_controls", "private_case_study", "public_case_study", "report_delivery", "policy_updates", "account_context")
    rows = []
    for rid in ids:
        row = {"id": rid, "status": "approved", "kind": "product_capability", "claim": "The example system exports reports.",
               "limit": "No quantified benefit is established.", "track": "A review can establish which reports the team needs.",
               "evidence": "The fictional system can export a report after a person selects its columns.",
               "source_reference": "products/example.md", "verticals": ["all"],
               "personas": ["operations_owner", "business_sponsor", "technical_evaluator", "economic_buyer"],
               "proof": {"name": None, "external_ok": False}, "approval_reference": "synthetic-test-only"}
        if rid == "report_setup":
            row.update(evidence="Export setup needs a reviewer by default.", personas=["operations_owner"])
        if rid == "data_exchange":
            row["verticals"] = ["technology", "financial_services", "professional_services"]
        if rid == "access_controls":
            row["claim"] = "The fictional 2026 release documents report controls."
        if rid == "private_case_study":
            row["proof"] = {"name": "Example Private Customer", "external_ok": False}
        if rid == "public_case_study":
            row["proof"] = {"name": "Example Public Customer", "external_ok": True}
        if rid == "policy_updates":
            row["proof"] = {"name": "Example Prospect", "external_ok": False}
        row["approved"] = approval.make_stamp(row, "2026-09-22")
        rows.append(row)
    factory.write(dest / "claims.json", {"claims": rows, "held": [], "source_revision": None,
        "source_root": "", "source_date": None, "evidence_verified": None})
    spec = [("operations_leader_appointment", 1, 90), ("public_operations_initiative", 1, 60), ("service_procurement", 1, 60),
            ("executive_statements", 2, 90), ("supplier_partnership", 2, 90), ("incumbent_standardization", 2, 90),
            ("paid_individuals_present", 2, 2), ("generic_marketing", 3, 90)]
    signals = []
    for sid, tier, freshness in spec:
        row = {"id": sid, "tier": tier, "freshness_days": freshness, "definition": "Synthetic account action.",
               "creates_work": "A report review", "target_titles": ["Chief Operating Officer", "Head of Operations", "CIO", "COO"],
               "claim_ids": [x for x in ids if x != "data_exchange"], "example_queries": ["example action"],
               "source": "adoption" if sid == "paid_individuals_present" else "web"}
        if sid == "supplier_partnership": row["claim_ids"].append("data_exchange")
        if sid == "executive_statements": row["target_titles"].append("the quoted executive")
        row["approved"] = approval.make_stamp(row, "2026-09-22")
        signals.append(row)
    factory.write(dest / "taxonomy.json", {"signals": signals})
    return dest


make_shared(SHARED)
