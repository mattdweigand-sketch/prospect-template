"""Read the canonical JSON factory. No connector calls or implicit example fallback."""
import json
import re
from pathlib import Path
from string import Formatter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "_shared"


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def domain(value):
    """Canonical host for identity comparisons, never a URL or a partial host."""
    require(nonblank(value) and not any(c.isspace() or ord(c) < 32 for c in value), "invalid domain")
    value = value[:-1] if value.endswith(".") else value
    try:
        value = value.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("invalid domain") from exc
    require(len(value) <= 253 and all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in value.split(".")), "invalid domain")
    return value


def email(value):
    """Validate one mailbox and normalize only its comparison identity."""
    require(isinstance(value, str) and value.count("@") == 1, "invalid email")
    local, host = value.split("@")
    require(bool(re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+", local)) and
            not local.startswith(".") and not local.endswith(".") and ".." not in local,
            "invalid email")
    host = domain(host)
    require("." in host and len(local) <= 64 and len(local + "@" + host) <= 254, "invalid email")
    return local.casefold() + "@" + host


def strings(value, empty=False):
    return (isinstance(value, list) and (empty or bool(value)) and
            all(nonblank(v) for v in value) and len(value) == len(set(value)))


def validate_lint(rules):
    require(isinstance(rules, dict), "outreach.lint must be an object")
    for key in ("forbidden_phrases", "forbidden_punctuation"):
        require(strings(rules.get(key), empty=True), f"outreach.lint.{key} must be a list of nonblank strings")
    require(type(rules.get("max_body_words")) is int and rules["max_body_words"] > 0,
            "outreach.lint.max_body_words must be a positive integer")
    for key in ("no_emoji", "no_hashtags", "no_markdown"):
        require(type(rules.get(key)) is bool, f"outreach.lint.{key} must be boolean")


def validate_policy(policy, sections=None):
    """Validate only the configuration consumed by the selected callable path."""
    require(isinstance(policy, dict) and policy.get("schema_version") == 2 and
            policy.get("mode") in ("example", "live"), "policy must use schema 2 and example/live mode")
    known = {"identity", "email_voice", "routing", "prospector", "outreach",
             "followup_signal", "scan", "adoption", "arr_growth", "refresh"}
    selected = known if sections is None else set(sections)
    require(selected <= known, "unknown policy section")

    def integer(obj, key, minimum=1):
        require(type(obj.get(key)) is int and obj[key] >= minimum, f"invalid policy.{section}.{key}")

    def words(obj, key, empty=False):
        require(strings(obj.get(key), empty), f"invalid policy.{section}.{key} list")

    def template(value, fields):
        require(nonblank(value), "template must be nonblank")
        try:
            parts = list(Formatter().parse(value))
        except ValueError as exc:
            raise ValueError("invalid template format") from exc
        require(all(field is None or (field in fields and not spec and not conversion)
                    for _, field, spec, conversion in parts), "unsupported template placeholder")

    for section in sorted(selected):
        obj = policy.get(section)
        require(isinstance(obj, dict), "configure policy." + section)
        if section == "identity":
            require(nonblank(obj.get("owner_id")), "configure owner ID")
            email(obj.get("owner_email"))
            require(nonblank(obj.get("timezone")), "configure timezone")
            try:
                ZoneInfo(obj["timezone"])
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError("invalid identity timezone") from exc
            words(obj, "internal_domains")
            for host in obj["internal_domains"]:
                domain(host)
        elif section == "email_voice":
            template(obj.get("greeting"), {"first_name"})
            require(all(nonblank(obj.get(k)) for k in ("closing", "body")), "configure email voice")
            require(obj.get("anchor_reference") is None or nonblank(obj["anchor_reference"]), "invalid voice anchor")
        elif section == "routing":
            words(obj, "house_owner_ids", empty=True)
            legacy = {"new": "propose account claim", "inactive_or_house_owner": "propose transfer only for configured owner IDs",
                      "owned_with_open_opportunity": "sales handoff", "owned_no_open_opportunity": "scan",
                      "other_active_owner": "owned_elsewhere"}
            require(all(k not in obj or obj[k] == v for k, v in legacy.items()), "deprecated routing descriptions cannot change fixed routes")
        elif section == "prospector":
            for key in ("max_candidates", "max_people_per_account", "adoption_candidate_rows"):
                integer(obj, key)
            for key in ("headcount_sources", "contact_email_sources"):
                words(obj, key)
            require(nonblank(obj.get("adoption_signal_id")), "configure adoption signal ID")
            require("admission" not in obj or obj["admission"] == "one tier1 or two distinct tier2 signals",
                    "deprecated admission cannot change fixed signal thresholds")
        elif section == "outreach":
            for key in ("activity_lookback_days", "bundle_max_age_hours", "subject_max_words", "max_drafts"):
                integer(obj, key)
            integer(obj, "suppression_days", 0)
            require(obj["activity_lookback_days"] >= obj["suppression_days"], "activity lookback must cover suppression")
            require(obj.get("fit_mode") in ("warn", "block"), "fit_mode must be warn or block")
            words(obj, "recipient_sources")
            words(obj, "suppressing_task_subtypes")
            task_status_map(obj)
            validate_lint(obj.get("lint"))
        elif section == "followup_signal":
            for key in ("due_calendar_days", "growth_due_business_days"):
                integer(obj, key, 0)
            integer(obj, "max_tasks")
            words(obj, "closed_statuses", empty=True)
            task = obj.get("task")
            require(isinstance(task, dict) and all(nonblank(task.get(k)) for k in ("status", "priority", "subtype")), "configure follow-up task fields")
            template(task.get("subject"), {"mail_subject"})
            template(task.get("description"), {"message_id", "thread_id", "signal_type", "claim_id"})
        elif section == "scan":
            integer(obj, "quote_min_words")
            integer(obj, "max_signals_per_account")
            warm = obj.get("warm_engagement")
            require(isinstance(warm, dict), "configure scan.warm_engagement")
            integer(warm, "lookback_days", 0)
            words(warm, "task_subject_markers")
            words(warm, "ignored_owner_ids", empty=True)
        elif section == "adoption":
            require(type(obj.get("enabled")) is bool, "adoption.enabled must be boolean")
            integer(obj, "data_lag_days", 0)
            statements = obj.get("approved_statements")
            require(isinstance(statements, dict) and set(statements) <= {"org_adopted", "individuals_only"} and
                    all(nonblank(v) for v in statements.values()), "only known positive adoption categories may have approved statements")
            keys = obj.get("bundle_keys")
            require(isinstance(keys, dict) and bool(keys) and all(nonblank(k) and t in ("str", "bool", "int", "list")
                    for k, t in keys.items()), "configure adoption.bundle_keys with supported types")
        elif section == "arr_growth":
            require(type(obj.get("enabled")) is bool, "arr_growth.enabled must be boolean")
            for key in ("window_days", "max_accounts", "candidate_rows"):
                integer(obj, key)
            for key in ("data_lag_days", "suppression_days"):
                integer(obj, key, 0)
            words(obj, "allowed_platforms")
            mail = obj.get("email_template")
            if obj["enabled"] or mail is not None:
                require(isinstance(mail, dict), "configure ARR email template")
                template(mail.get("subject"), set())
                template(mail.get("body"), set())
                template(mail.get("greeting_person"), {"first_name"})
                template(mail.get("greeting_team"), {"account_name"})
        elif section == "refresh":
            require(obj.get("source") is None or nonblank(obj["source"]), "invalid refresh source")
            for key in ("clone_depth", "max_new_rows"):
                integer(obj, key)
            for key in ("watch_dirs", "watch_paths", "ignore_pages"):
                words(obj, key, empty=True)
            paths = obj["watch_dirs"] + obj["watch_paths"] + obj["ignore_pages"]
            for key in ("icp_path", "contradictions_path"):
                require(obj.get(key) is None or nonblank(obj[key]), "invalid refresh path: " + key)
                if obj.get(key) is not None:
                    paths.append(obj[key])
            require(all(not Path(p).is_absolute() and ".." not in Path(p).parts and
                        not any(ord(c) < 32 for c in p) for p in paths), "refresh paths must be safe relative paths")


def read(path):
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {Path(path).name}")
    return value


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def task_status_map(outreach):
    """Reviewed provider status -> normalized task state; no inferred defaults."""
    mapping = outreach.get("task_status_map")
    if not isinstance(mapping, dict) or any(
            not isinstance(native, str) or not native.strip() or
            not isinstance(state, str) or state not in ("completed", "open", "cancelled")
            for native, state in mapping.items()):
        raise ValueError("outreach.task_status_map must map provider statuses to completed, open or cancelled")
    return mapping


def frontmatter(shared=SHARED):
    text = (Path(shared) / "icp.md").read_text()
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("icp.md needs JSON frontmatter between --- lines")
    value = json.loads(text[4:].split("\n---\n", 1)[0])
    if not isinstance(value, dict):
        raise ValueError("icp.md frontmatter must be an object")
    return value


def write_frontmatter(shared, value):
    path = Path(shared) / "icp.md"
    text = path.read_text()
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("icp.md needs JSON frontmatter between --- lines")
    body = text[4:].split("\n---\n", 1)[1]
    path.write_text("---\n" + json.dumps(value, indent=2) + "\n---\n" + body)


def taxonomy(shared=SHARED):
    """Group the canonical flat signal list by tier for workflow checks."""
    doc = read(Path(shared) / "taxonomy.json")
    tiers = {"tier1": [], "tier2": [], "tier3": []}
    seen = set()
    for row in doc["signals"]:
        if row["id"] in seen or type(row["tier"]) is not int or row["tier"] not in (1, 2, 3):
            raise ValueError("duplicate signal id or invalid tier")
        seen.add(row["id"])
        tiers[f"tier{row['tier']}"].append(row)
    return {**doc, "tiers": tiers}


def claim_document(shared=SHARED):
    doc = read(Path(shared) / "claims.json")
    ids = [r["id"] for r in doc["claims"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate claim id")
    return doc


def relative_path(root, ref):
    """Constrain source references and generated outputs to their declared root."""
    ref = Path(ref)
    root = Path(root).resolve()
    if ref.is_absolute() or ".." in ref.parts:
        raise ValueError("path must stay inside its declared root")
    path = root / ref
    if any((root / part).is_symlink() for part in (ref, *ref.parents)):
        raise ValueError("source path must not contain symlinks")
    if not path.resolve().is_relative_to(root):
        raise ValueError("path escapes its declared root")
    return path


def validate_examples(root=ROOT):
    """Validate shipped example cross-references without opening private configuration."""
    shared = Path(root) / "_shared"
    pol = read(shared / "policy.example.json")
    claims = read(shared / "claims.example.json")["claims"]
    signals = read(shared / "taxonomy.example.json")["signals"]
    fm = json.loads((shared / "icp.example.md").read_text().split("---", 2)[1])
    errors = []
    validate_policy(pol)
    if pol.get("schema_version") != 2 or pol.get("mode") != "example":
        errors.append("example policy must be schema 2 in example mode")
    if pol["adoption"]["enabled"] or pol["arr_growth"]["enabled"] or pol["arr_growth"]["email_template"] is not None:
        errors.append("private example capabilities must be disabled and the billing template unconfigured")
    if pol["outreach"]["activity_lookback_days"] < pol["outreach"]["suppression_days"]:
        errors.append("activity lookback must cover the entire suppression window")
    claim_ids, signal_ids = [r["id"] for r in claims], [s["id"] for s in signals]
    if len(set(claim_ids)) != len(claim_ids) or len(set(signal_ids)) != len(signal_ids):
        errors.append("example claim and signal IDs must be unique")
    bound = set()
    for signal in signals:
        if type(signal["tier"]) is not int or signal["tier"] not in (1, 2, 3) or signal["source"] not in ("web", "adoption"):
            errors.append("invalid example signal tier/source")
        if type(signal["freshness_days"]) is not int or signal["freshness_days"] < 0:
            errors.append("invalid example signal freshness")
        if signal.get("approved") is not None:
            errors.append("example signals must be unapproved")
        if not isinstance(signal.get("example_queries"), list) or any(not isinstance(q, str) or not q.strip() for q in signal["example_queries"]):
            errors.append("example signals need an example_queries list")
        bound.update(signal["claim_ids"])
    if bound != set(claim_ids):
        errors.append("example bindings must reference every claim and no unknown claims")
    kinds = {"reported_example", "product_capability", "inference", "evaluation_advice"}
    verticals = {v["id"] for v in fm["verticals"]} | {"all"}
    personas = set(fm["persona_cares"])
    for row in claims:
        required = {"id", "status", "kind", "claim", "limit", "track", "evidence", "source_reference", "verticals", "personas", "proof", "approved", "approval_reference"}
        if not required <= set(row):
            errors.append("example claim is missing required fields")
        if row["status"] != "example" or row["kind"] not in kinds or row.get("approved") is not None:
            errors.append("example claims must have a recognized kind and remain unapproved examples")
        if not set(row["verticals"]) <= verticals or not set(row["personas"]) <= personas:
            errors.append("example claim references an unknown vertical/persona")
    if fm.get("persona_cares_approved") is not None:
        errors.append("example personas must be unapproved")
    return errors
