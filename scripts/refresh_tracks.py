#!/usr/bin/env python3
"""Inspect claim evidence at a pinned Git revision; prepare reviewed postimages in a separate staging directory.

No source-repository writes, network calls or active-configuration writes. A prepared
stamp is proposed content, not proof of approval. Apply through workflows/run.md.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import approval
import factory

SHARED = factory.SHARED
WIKILINK = re.compile(r"\[\[([^\]|#]+)")


def norm(value):
    return re.sub(r"\s+", " ", value or "").strip().lower()


def git(wiki, *args):
    result = subprocess.run(["git", "-C", str(wiki), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def source_path(root, ref):
    for part in (root, ref):
        if not isinstance(part, str) or Path(part).is_absolute() or ".." in Path(part).parts or "\n" in part or "\t" in part:
            raise ValueError("source references must be relative paths inside the pinned repository")
    return str(Path(root) / ref)


def page_at(wiki, revision, root, ref):
    path = source_path(root, ref)
    tree = git(wiki, "ls-tree", revision, "--", path)
    if not tree:
        return None
    if not tree.startswith("100644 blob ") and not tree.startswith("100755 blob "):
        raise ValueError("source reference must identify a regular committed file")
    return git(wiki, "show", f"{revision}:{path}")


def verify_rows(rows, wiki_root):
    """Local synthetic-fixture helper. Production reports use page_at at the pinned commit."""
    broken, missing = [], []
    for row in rows:
        page = factory.relative_path(wiki_root, row["source_reference"])
        if not page.is_file():
            missing.append({"id": row["id"], "source_reference": row["source_reference"]})
        elif not row.get("evidence") or norm(row["evidence"]) not in norm(page.read_text()):
            broken.append({"id": row["id"], "source_reference": row["source_reference"]})
    return broken, missing


def changed_pages(name_status, source_root, watch_dirs, ignore_pages):
    prefix = source_root.strip("/") + "/" if source_root else ""
    out = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or not parts[-1].startswith(prefix):
            continue
        rel = parts[-1][len(prefix):]
        if rel not in ignore_pages and rel.split("/", 1)[0] in watch_dirs and parts[0][0] in "AM":
            out.append({"status": "added" if parts[0][0] == "A" else "modified", "path": rel})
    return out


def changed_watch_files(name_status, source_root, watch_files):
    prefix = source_root.strip("/") + "/" if source_root else ""
    return [parts[-1][len(prefix):] for line in name_status.splitlines() for parts in [line.split("\t")]
            if len(parts) >= 2 and parts[-1].startswith(prefix) and parts[-1][len(prefix):] in watch_files]


def contradiction_flags(text, rows):
    open_part = text.split("## Open", 1)[-1].split("## Resolved", 1)[0]
    refs = {}
    for row in rows:
        refs.setdefault(Path(row["source_reference"]).stem.lower(), []).append(row)
    out = []
    for entry in re.split(r"^### ", open_part, flags=re.M)[1:]:
        title = entry.splitlines()[0].strip()
        if title.lower().startswith("[status: open]"):
            for link in {Path(x.strip().lower()).stem for x in WIKILINK.findall(entry)}:
                for row in refs.get(link, []):
                    out.append({"id": row["id"], "source_reference": row["source_reference"], "contradiction": title.split("]", 1)[-1].strip()})
    return out


def unstamped(doc, tax, fm):
    out = [{"unit": "row", "id": r["id"]} for r in doc["claims"] if not approval.stamp_current(r, r.get("approved"))]
    out += [{"unit": "signal", "id": r["id"]} for r in tax["signals"] if r["tier"] in (1, 2) and not approval.stamp_current(r, r.get("approved"))]
    if not approval.stamp_current(fm["persona_cares"], fm.get(approval.PERSONA_STAMP_KEY)):
        out.append({"unit": "persona_cares", "id": "icp.md"})
    return out


def load(shared):
    return factory.claim_document(shared), factory.taxonomy(shared), factory.frontmatter(shared), factory.read(shared / "policy.json")["refresh"]


def report(wiki, shared=SHARED, revision="HEAD"):
    doc, tax, fm, pol = load(shared)
    head = git(wiki, "rev-parse", "--verify", f"{revision}^{{commit}}")
    prior = doc.get("source_revision")
    previous = git(wiki, "rev-parse", "--verify", f"{prior}^{{commit}}") if prior else None
    root = doc["source_root"]
    source_path(root, "")
    broken, missing = [], []
    for row in doc["claims"]:
        text = page_at(wiki, head, root, row["source_reference"])
        if text is None:
            missing.append({"id": row["id"], "source_reference": row["source_reference"]})
        elif not row.get("evidence") or norm(row["evidence"]) not in norm(text):
            broken.append({"id": row["id"], "source_reference": row["source_reference"]})
    if previous:
        diff = git(wiki, "diff", "--no-renames", "--name-status", f"{previous}..{head}", "--", root or ".")
    else:
        diff = "\n".join("A\t" + p for p in git(wiki, "ls-tree", "--name-only", "-r", head, "--", root or ".").splitlines())
    contradiction = page_at(wiki, head, root, pol["contradictions_path"]) if pol.get("contradictions_path") else None
    watched = list(dict.fromkeys(pol["watch_paths"] + [p for p in (pol.get("icp_path"), pol.get("contradictions_path")) if p]))
    missing_watch = [ref for ref in watched if page_at(wiki, head, root, ref) is None]
    return {"head": head, "head_date": git(wiki, "show", "-s", "--format=%cs", head), "source_revision": prior,
            "unchanged": previous == head, "rows": len(doc["claims"]), "broken_rows": broken, "missing_pages": missing,
            "changed_pages": changed_pages(diff, root, pol["watch_dirs"], pol["ignore_pages"]),
            "changed_watch_files": changed_watch_files(diff, root, watched),
            "missing_watch_pages": missing_watch,
            "contradiction_flags": contradiction_flags(contradiction or "", doc["claims"]),
            "unstamped": unstamped(doc, tax, fm)}


def write_tracks(doc, path):
    factory.write(path, doc)


def stamp(rep, shared=SHARED, today=None):
    if rep["broken_rows"] or rep["missing_pages"] or rep.get("missing_watch_pages"):
        raise ValueError("fix broken evidence and missing pages before stamping the source revision")
    path = shared / "claims.json"
    doc = factory.read(path)
    doc.update(source_revision=rep["head"], source_date=rep["head_date"], evidence_verified=today or date.today().isoformat())
    factory.write(path, doc)


def stamp_units(rows, ids, today):
    ids = set(ids)
    known = {r["id"] for r in rows}
    if not ids or not ids <= known:
        raise ValueError("name exact known units; wildcard approvals are unsupported")
    for row in rows:
        if row["id"] in ids:
            row["approved"] = approval.make_stamp(row, today)
    return [r["id"] for r in rows if r["id"] in ids]


def approve_rows(ids, shared=SHARED, today=None):
    path = shared / "claims.json"
    doc = factory.read(path)
    done = stamp_units(doc["claims"], ids, today or date.today().isoformat())
    factory.write(path, doc)
    return done


def approve_signals(ids, shared=SHARED, today=None):
    path = shared / "taxonomy.json"
    doc = factory.read(path)
    done = stamp_units(doc["signals"], ids, today or date.today().isoformat())
    factory.write(path, doc)
    return done


def approve_persona_cares(shared=SHARED, today=None):
    fm = factory.frontmatter(shared)
    result = approval.make_stamp(fm["persona_cares"], today or date.today().isoformat())
    fm[approval.PERSONA_STAMP_KEY] = result
    factory.write_frontmatter(shared, fm)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wiki", type=Path, required=True)
    ap.add_argument("--shared", type=Path, default=SHARED)
    ap.add_argument("--revision", default="HEAD")
    ap.add_argument("--stage", type=Path, help="new directory for proposed factory postimages; never the active factory")
    ap.add_argument("--stamp", action="store_true")
    ap.add_argument("--approve-rows")
    ap.add_argument("--approve-signals")
    ap.add_argument("--approve-persona-cares", action="store_true")
    a = ap.parse_args()
    try:
        rep = report(a.wiki, a.shared, a.revision)
        mutating = a.stamp or a.approve_rows or a.approve_signals or a.approve_persona_cares
        if mutating and not a.stage:
            raise ValueError("stamp preparation requires --stage; active configuration is never mutated")
        if a.stage:
            if a.stage.exists() or a.stage.is_symlink():
                raise ValueError("stage must be a new directory")
            if a.stage.resolve().is_relative_to(a.shared.resolve()):
                raise ValueError("stage must be outside the input factory")
            # All validation precedes writes to the proposed destination.
            if a.stamp and (rep["broken_rows"] or rep["missing_pages"] or rep["missing_watch_pages"]):
                raise ValueError("cannot stamp broken or missing evidence")
            doc, tax, _, _ = load(a.shared)
            for requested, rows in ((a.approve_rows, doc["claims"]), (a.approve_signals, tax["signals"])):
                if requested and not set(requested.split(",")) <= {r["id"] for r in rows}:
                    raise ValueError("name exact known units; wildcard approvals are unsupported")
            a.stage.mkdir(parents=True)
            for name in ("policy.json", "claims.json", "taxonomy.json", "icp.md"):
                shutil.copyfile(a.shared / name, a.stage / name)
            if a.approve_rows:
                approve_rows(a.approve_rows.split(","), a.stage)
            if a.approve_signals:
                approve_signals(a.approve_signals.split(","), a.stage)
            if a.approve_persona_cares:
                approve_persona_cares(a.stage)
            if a.stamp:
                stamp(rep, a.stage)
            rep["stage"] = str(a.stage)
            rep["stage_status"] = "proposed_only_requires_exact_review"
        print(json.dumps(rep, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({"verdict": "error", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
