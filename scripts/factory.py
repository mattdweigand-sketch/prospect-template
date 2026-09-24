"""Read the canonical JSON factory. No connector calls or implicit example fallback."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "_shared"


def read(path):
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {Path(path).name}")
    return value


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


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
