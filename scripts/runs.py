#!/usr/bin/env python3
"""Copy a run starter and inspect its review state. Never calls an external service."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

from wrappers import ROOT, load_routes

RUN_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")


def run_path(root, run_id):
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("run ID must be 1-80 lowercase letters, digits or hyphens")
    path = root / "output" / run_id
    if (root / "output").is_symlink() or path.is_symlink():
        raise ValueError("run directory must not be a symlink")
    return path


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or symlinked file: " + str(path))
    return path


def init(root, run_id, workflow):
    if workflow not in load_routes(root):
        raise ValueError("unknown workflow: " + workflow)
    dest = run_path(root, run_id)
    if dest.exists():
        raise ValueError("run already exists; select a fresh task-supplied ID")
    source = root / "_templates/run"
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("run starter contains a symlink")
    dest.parent.mkdir(exist_ok=True)
    shutil.copytree(source, dest)
    regular(dest / "request.md").write_text(
        f"---\nrun_id: {run_id}\nworkflow: {workflow}\n---\n\n"
        "# Request\n\nRecord the user's request, exact scope, and input paths here before work.\n"
    )
    return dest


def workflow_name(path, root):
    text = regular(path / "request.md").read_text()
    match = re.search(r"^workflow: ([a-z0-9-]+)$", text, re.M)
    identity = re.search(r"^run_id: ([a-z0-9-]+)$", text, re.M)
    if not match or match[1] not in load_routes(root) or not identity or identity[1] != path.name:
        raise ValueError("request must identify this run and a known workflow")
    return match[1]


def snapshot(root, path):
    name = workflow_name(path, root)
    route = load_routes(root)[name]
    files = [path / "request.md", path / "01_review.md", root / "_shared/policy.json",
             root / "_shared/rules.md", root / "workflows/run.md", root / route["workspace"], root / route["workflow"]]
    # Each repo names additional stable inputs in the policy's review_inputs.
    policy = json.loads(regular(root / "_shared/policy.json").read_text())
    for ref in policy.get("review_inputs", []):
        rel = Path(ref)
        if rel.is_absolute() or ".." in rel.parts or not str(rel).startswith("_shared/"):
            raise ValueError("review inputs must be paths inside _shared/")
        files.append(root / rel)
    for ref in review_metadata(path).get("artifacts", []):
        rel = Path(ref)
        if rel.is_absolute() or ".." in rel.parts or ref in ("review.json", "02_result.json"):
            raise ValueError("review artifacts must be source or output files inside this run")
        target = path / rel
        if any((path / p).is_symlink() for p in [rel] + list(rel.parents)):
            raise ValueError("review artifact path must not contain symlinks")
        files.append(target)
    return {str(p.relative_to(root)): hashlib.sha256(regular(p).read_bytes()).hexdigest() for p in files}


def review_metadata(path):
    text = regular(path / "01_review.md").read_text()
    header = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not header:
        raise ValueError("review needs flat YAML frontmatter")
    meta = {}
    for line in header[1].splitlines():
        key, sep, value = line.partition(": ")
        if not sep or key not in ("status", "expected_after", "artifacts") or key in meta:
            raise ValueError("invalid or duplicate review metadata field")
        meta[key] = value if key == "status" else json.loads(value)
    artifacts = meta.get("artifacts", [])
    if not isinstance(artifacts, list) or any(not isinstance(v, str) or not v for v in artifacts):
        raise ValueError("artifacts must be a JSON list of run-relative paths")
    if len(artifacts) != len(set(artifacts)):
        raise ValueError("duplicate review artifact path")
    return meta


def proposal(path):
    text = regular(path / "01_review.md").read_text()
    if review_metadata(path).get("status") != "ready":
        raise ValueError("review artifact is still draft; finish the workflow's checks first")
    ids = re.findall(r"^## Effect ([a-zA-Z0-9-]+)$", text, re.M)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate effect IDs")
    return ids


def expected_after(path, effect_ids, before):
    changes = review_metadata(path).get("expected_after", {})
    if not isinstance(changes, dict) or not set(changes) <= set(proposal(path)):
        raise ValueError("expected_after must map proposed effect IDs to file hashes")
    expected = {}
    for effect, files in changes.items():
        if not isinstance(files, dict):
            raise ValueError("expected_after file revisions must be objects")
        for ref, digest in files.items():
            if ref not in before or not ref.startswith("_shared/") or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("expected_after must hash a declared shared input")
            if effect in effect_ids:
                if ref in expected and expected[ref] != digest:
                    raise ValueError("conflicting postimages for " + ref)
                expected[ref] = digest
    return expected


def record_review(root, run_id, reviewer, approval_ref, effect_ids):
    path = run_path(root, run_id)
    proposed = proposal(path)
    if not reviewer.strip() or not approval_ref.strip():
        raise ValueError("a reviewer and actual conversation reference are required")
    if len(effect_ids) != len(set(effect_ids)) or not set(effect_ids) <= set(proposed):
        raise ValueError("approved effects must be unique IDs in the reviewed proposal")
    before = snapshot(root, path)
    after = expected_after(path, effect_ids, before)
    doc = {"reviewer": reviewer, "approval_reference": approval_ref,
           "reviewed_at": datetime.now(timezone.utc).isoformat(),
           "approved_effect_ids": effect_ids, "snapshot": before, "expected_after": after}
    regular(path / "review.json").write_text(json.dumps(doc, indent=2) + "\n")
    return doc


def status(root, run_id):
    path = run_path(root, run_id)
    workflow_name(path, root)
    try:
        proposed = proposal(path)
    except ValueError as exc:
        return {"state": "draft", "reason": str(exc)}
    doc = json.loads(regular(path / "review.json").read_text())
    if not doc.get("reviewer") or not doc.get("approval_reference"):
        return {"state": "awaiting_human_review"}
    current = snapshot(root, path)
    before = doc.get("snapshot") or {}
    approved = doc.get("approved_effect_ids")
    if not isinstance(approved, list) or len(approved) != len(set(approved)) or not set(approved) <= set(proposed):
        raise ValueError("review contains invalid effect IDs")
    after = expected_after(path, approved, before)
    if doc.get("expected_after", {}) != after:
        return {"state": "review_stale"}
    changed = {ref for ref in current if current[ref] != before.get(ref)}
    if set(before) != set(current) or any(current[ref] != after.get(ref) for ref in changed):
        return {"state": "review_stale"}
    result = json.loads(regular(path / "02_result.json").read_text())
    if not result.get("recorded_at"):
        return {"state": "recovery_required" if changed else "review_current", "approved_effect_ids": approved}
    if result.get("review_snapshot") != doc["snapshot"]:
        return {"state": "result_stale"}
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise ValueError("result needs a summary")
    effects = result.get("effects")
    if not isinstance(effects, list) or any(not isinstance(e, dict) for e in effects):
        raise ValueError("result effects must be objects")
    ids = [e.get("id") for e in effects]
    if len(ids) != len(set(ids)) or set(ids) != set(approved):
        raise ValueError("result must account for exactly the approved effects")
    for row in effects:
        if row.get("status") not in ("verified", "pending", "failed", "skipped"):
            raise ValueError("invalid effect result status")
        if row["status"] == "verified" and (not row.get("provider_reference") or not row.get("readback_reference")):
            raise ValueError("verified result needs provider and readback references")
    incomplete = [e["id"] for e in effects if e["status"] != "verified"]
    if any(current[ref] != digest for ref, digest in after.items()):
        return {"state": "incomplete", "reason": "approved local file revisions have not all landed"}
    return {"state": "incomplete" if incomplete else "completion_recorded",
            "unresolved_effect_ids": incomplete,
            "note": "Local records do not prove human authorization or provider success. Inspect the cited evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    start = subs.add_parser("init")
    start.add_argument("run_id")
    start.add_argument("workflow")
    show = subs.add_parser("status")
    show.add_argument("run_id")
    review = subs.add_parser("record-review")
    review.add_argument("run_id")
    review.add_argument("--reviewer", required=True)
    review.add_argument("--approval-ref", required=True)
    review.add_argument("--effects", nargs="*", default=[])
    args = parser.parse_args()
    try:
        if args.action == "init":
            print(init(ROOT, args.run_id, args.workflow))
        elif args.action == "status":
            print(json.dumps(status(ROOT, args.run_id), indent=2))
        else:
            record_review(ROOT, args.run_id, args.reviewer, args.approval_ref, args.effects)
            print("Review reference recorded. This command cannot grant authorization.")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
