#!/usr/bin/env python3
"""Select self-serve accounts with ARR growth and emit the exact template draft for each. signal-arr-growth calls this once per run.

Usage:
    python3 workflows/signal-arr-growth/arr_growth_gate.py --packet packet.json [--today YYYY-MM-DD]
    python3 workflows/signal-arr-growth/arr_growth_gate.py --queries accounts.json [--today YYYY-MM-DD]
    --today is for tests. Default is today in identity.timezone.
    --queries takes {"accounts": [{"id": "account-123", "website": "https://acme.example"}]} and emits structured
    task/event and sent-email read intents per account. A missing usable Website domain holds that account.

packet.json
    {
      "data_through_date": "2026-09-20",
      "rows": [                                   # rows from arr_growth_source.sql, in the order returned, each joined to live CRM reads
        {
          "organization_uuid": "...", "organization_name": "...", "crm_account_id": "account-123",
          "baseline_arr_usd": 1200.0, "current_arr_usd": 2400.0, "net_change_usd": 1200.0,
          "observed_dates": 31, "required_dates": 31,
          "subscription_platform": "web", "billing_email": "x@acme.example", "communications_enabled": true,
          "account": {"exists": true, "name": "Acme", "website": "https://acme.example", "owner_id": "owner-123", "owner_is_active": true,
                      "open_deal_ids": [], "headcount": 1200, "headcount_source": "account.headcount"},
          "contacts": [ {"id": "contact-123", "email": "x@acme.example", "first_name": "Jane"} ],   # Contacts on the Account whose Email equals billing_email
          "last_touch_date": "2026-09-01" | null,   # most recent Email or Call Task or Event on the Account, or email provider send to anyone at its email domain
          "reads": {"account": true, "deals": true, "contacts": true, "tasks": true,
                    "events": true, "email_sent": true, "headcount_lookup": false}
        }
      ]
    }

Per row, in order. The first failure names the hold.
    1. data: data_through_date is yesterday in identity.timezone. Coverage is window_days + 1;
       ARR amounts are finite and nonnegative (malformed amounts are exit 2), and positive net change agrees
       with current minus baseline
    2. route: Account exists and routes `scan` (identity.crm_user_id owns it, no open deal). Other routes are reported as the hold
    3. territory: headcount inside icp.md frontmatter. Unknown holds. A completed headcount lookup is
       required when headcount is absent or headcount_source is not account.headcount
    4. recipient: billing_email present, subscription_platform equals arr_growth.recipient_platform, communications_enabled true
    5. contacts: zero or one Contact matching the recipient. Two or more holds. A usable Account Website
       domain and completed contacts, tasks, events, and email_sent reads are required before selection
    6. suppression: last_touch_date null, or before today - arr_growth.suppression_days. A touch on the boundary day holds,
       the same rule as outreach_gate.py
    7. draft: subject and body from arr_growth.draft. Greeting from the one Contact's first_name, else the team form.
       Subject and body (greeting excluded) must not match arr_growth.draft_forbidden_pattern, compiled case-insensitively.
       A match is a template error, exit 2, because the template is policy, not row data. A blank or NULL
       Contact first name uses the existing team greeting. At most one eligible row per Account is selected

reads records completed native reads, including successful empty results. It does not prove provider authenticity or
authorization. Account and deals reads precede routing; later reads are required only after earlier holds clear.

Selected rows keep query order up to max_accounts_per_run. Exit 0 when at least one is selected, 1 when none, 2 unusable input
or a forbidden template. The exit 2 envelope is {"verdict": "error", "reason": "..."}. Always JSON on stdout.
"""
import argparse
import json
import math
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared" / "scripts"))
import common  # noqa: E402
from route_candidate import load_rules, route, territory  # noqa: E402

SHARED = common.SHARED
ROW_KEYS = {"organization_uuid", "organization_name", "crm_account_id", "baseline_arr_usd", "current_arr_usd",
            "net_change_usd", "observed_dates", "required_dates", "subscription_platform", "billing_email",
            "communications_enabled", "account", "contacts", "last_touch_date", "reads"}


def account_domain(website):
    """A DNS email domain from an Account Website; unusable inputs remain unknown."""
    if not isinstance(website, str) or not website.strip():
        return None
    value = website.strip()
    try:
        parsed = urlsplit(value if "://" in value else "https://" + value)
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
            return None
        domain = (parsed.hostname or "").lower().removeprefix("www.")
        parsed.port  # reject malformed ports
    except ValueError:
        return None
    labels = domain.split(".")
    if len(domain) > 253 or len(labels) < 2 or labels[-1].isdigit():
        return None
    if not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
        return None
    return domain


def queries(packet, policy, today=None):
    """Structured read intents, never provider query text or evidence of completed reads."""
    today = today or common.policy_today(policy)
    cutoff = today - timedelta(days=policy["arr_growth"]["suppression_days"])
    timestamp = datetime.combine(cutoff, time.min, tzinfo=common.policy_tz(policy)).isoformat()
    subtypes = policy["outreach"]["suppressing_task_subtypes"]
    if not isinstance(subtypes, list) or not subtypes or any(not common.opaque_id(v) for v in subtypes):
        raise ValueError("suppressing_task_subtypes must be a nonempty list of subtype names")
    accounts = packet.get("accounts")
    if not isinstance(accounts, list):
        raise ValueError("accounts must be a list")
    out = []
    for account in accounts:
        aid = account.get("id")
        if not common.opaque_id(aid):
            raise ValueError("read account id must be a nonempty opaque string")
        domain = account_domain(account.get("website"))
        if not domain:
            out.append({"account_id": aid, "hold": "account_domain_missing"})
            continue
        out.append({"account_id": aid, "account_domain": domain,
                    "tasks": {"capability": "crm.query", "entity": "task",
                              "filters": {"account_id": aid, "date_gte": cutoff.isoformat(), "subtypes": subtypes}},
                    "events": {"capability": "crm.query", "entity": "event",
                               "filters": {"account_id": aid, "date_gte": cutoff.isoformat()}},
                    "email_sent": {"capability": "email.search",
                                   "filters": {"is_sent": True, "recipient_domain": domain, "sent_at_gte": timestamp}}})
    return {"cutoff_date": cutoff.isoformat(), "queries": out}


def forbidden(pol):
    """arr_growth.draft_forbidden_pattern compiled once per run. Case-insensitive so 'arr' and 'ARR' both match."""
    return re.compile(pol["draft_forbidden_pattern"], re.I)


def valid_amount(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def hold_reason(r, rules, pol, today):
    amounts = [r[k] for k in ("baseline_arr_usd", "current_arr_usd", "net_change_usd")]
    if not all(valid_amount(v) for v in amounts):
        raise ValueError("ARR amounts must be finite, nonnegative numbers")
    required = pol["window_days"] + 1
    if any(type(r[key]) is not int or r[key] != required for key in ("observed_dates", "required_dates")):
        return "incomplete_daily_coverage"
    if r["net_change_usd"] <= 0:
        return "no_positive_net_change"
    delta = r["current_arr_usd"] - r["baseline_arr_usd"]
    if delta <= 0 or not math.isclose(delta, r["net_change_usd"], rel_tol=0, abs_tol=0.005):
        return "inconsistent_net_change"
    reads = r["reads"]
    if not isinstance(reads, dict):
        raise ValueError("reads must be an object of completed native reads")
    if reads.get("account") is not True:
        return "read_not_completed:account"
    a = r["account"]
    if not isinstance(a.get("exists"), bool):
        raise ValueError("account.exists must be a boolean")
    if not a["exists"]:
        return "no_crm_account"
    if reads.get("deals") is not True:
        return "read_not_completed:deals"
    rt = route({"account_exists": True, "owner_id": a.get("owner_id"), "owner_is_active": a.get("owner_is_active"),
                "open_deal_ids": a.get("open_deal_ids")}, rules)
    if rt != "scan":
        return rt
    if (a.get("headcount") is None or a.get("headcount_source") != "account.headcount") \
            and reads.get("headcount_lookup") is not True:
        return "read_not_completed:headcount_lookup"
    t = territory(a.get("headcount"), rules)
    if t != "in":
        return f"territory_{t}"
    if not r["billing_email"]:
        return "billing_email_missing"
    if r["subscription_platform"] != pol["recipient_platform"]:
        return "unsupported_billing_platform"
    if r["communications_enabled"] is not True:
        return "communications_disabled"
    if not account_domain(a.get("website")):
        return "account_domain_missing"
    for key in ("contacts", "tasks", "events", "email_sent"):
        if reads.get(key) is not True:
            return f"read_not_completed:{key}"
    if not isinstance(r["contacts"], list):
        raise ValueError("contacts must be a list")
    if len(r["contacts"]) > 1:
        return "ambiguous_contact"
    for c in r["contacts"]:
        if (c.get("email") or "").lower() != r["billing_email"].lower():
            return "contact_email_mismatch"
    if r["last_touch_date"] is not None:
        if date.fromisoformat(r["last_touch_date"]) >= today - timedelta(days=pol["suppression_days"]):
            return "suppressed_recent_touch"
    return None


def build_draft(r, pol, forbid):
    d = pol["draft"]
    first = r["contacts"][0].get("first_name") if r["contacts"] else None
    if isinstance(first, str) and first.strip().lower() == "null":
        first = None
    greeting = d["greeting_person"].format(first_name=first.strip()) if first and first.strip() \
        else d["greeting_team"].format(account_name=r["account"]["name"])
    body = d["body"].rstrip("\n")
    hit = forbid.search(d["subject"]) or forbid.search(body)
    if hit:
        raise ValueError(f"draft template contains a forbidden token {hit.group(0)!r}. Fix arr_growth.draft in policy.yaml")
    return {"to": r["billing_email"], "subject": d["subject"], "body": f"{greeting}\n\n{body}"}


def check(packet, policy, today=None, shared=SHARED):
    pol = policy["arr_growth"]
    rules = load_rules(shared)
    forbid = forbidden(pol)
    today = today or common.policy_today(policy)
    expected_date = (today - timedelta(days=1)).isoformat()
    if packet.get("data_through_date") != expected_date:
        raise ValueError(f"data_through_date must be the complete data date {expected_date}")
    rows = packet.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    selected, held, selected_accounts = [], [], set()
    for i, r in enumerate(rows, 1):
        missing = sorted(ROW_KEYS - set(r))
        if missing:
            raise ValueError(f"row {i} missing keys: {missing}")
        if not isinstance(r["crm_account_id"], str) or not r["crm_account_id"].strip():
            raise ValueError(f"row {i} needs a nonempty crm_account_id")
        reason = hold_reason(r, rules, pol, today)
        entry = {"rank": i, "account_id": r["crm_account_id"], "account_name": r["account"].get("name") or r["organization_name"],
                 "net_change_usd": r["net_change_usd"], "baseline_arr_usd": r["baseline_arr_usd"], "current_arr_usd": r["current_arr_usd"]}
        if reason:
            held.append({**entry, "hold": reason})
        elif r["crm_account_id"] in selected_accounts:
            held.append({**entry, "hold": "duplicate_account"})
        elif len(selected) < pol["max_accounts_per_run"]:
            selected.append({**entry, "headcount": r["account"]["headcount"], "headcount_source": r["account"].get("headcount_source"),
                             "contact_id": r["contacts"][0]["id"] if r["contacts"] else None, "draft": build_draft(r, pol, forbid)})
            selected_accounts.add(r["crm_account_id"])
        else:
            held.append({**entry, "hold": "over_max_accounts_per_run"})
    return {"verdict": "allow" if selected else "block", "data_through_date": packet.get("data_through_date"),
            "selected": selected, "held": held, "shortfall": max(0, pol["max_accounts_per_run"] - len(selected))}


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--packet")
    mode.add_argument("--queries", help="JSON accounts list for provider-neutral suppression read intents")
    ap.add_argument("--shared", default=str(SHARED))
    ap.add_argument("--today", default=None, help="YYYY-MM-DD, tests only. Default is today in identity.timezone")
    a = ap.parse_args()
    try:
        shared = Path(a.shared)
        packet = json.loads(Path(a.packet or a.queries).read_text())
        policy = common.load_policy(shared)
        today = date.fromisoformat(a.today) if a.today else None
        out = queries(packet, policy, today) if a.queries else check(packet, policy, today, shared=shared)
        encoded = json.dumps(out, indent=2, allow_nan=False)
    except common.INPUT_ERRORS as e:
        print(common.error_json(e))
        return 2
    print(encoded)
    return 0 if a.queries or out["verdict"] == "allow" else 1


if __name__ == "__main__":
    sys.exit(main())
