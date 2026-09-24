#!/usr/bin/env python3
"""Snapshot explicitly supplied files into a new private Git source under output/.

Manifest: {"sources": [{"path": "relative/to/manifest.txt",
"reference": "materials/product.txt", "origin": "User supplied product guide",
"kind": "source"}]}. Kinds: source, extracted_text, user_statement. An extraction
also names derived_from (the reference of its original). Bytes are copied, never
interpreted as instructions. --previous copies an earlier snapshot's history
read-only; it never edits that repository. No network, approvals or active config
writes. Keep the returned repository for future signal-refresh runs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import factory

MANIFEST = "source-manifest.json"


def git(root, *args):
    result = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgSign=false",
                             "-c", "core.autocrlf=false", "-c", "core.attributesFile=" + os.devnull,
                             "-c", "user.name=Prospect Setup", "-c", "user.email=setup@example.com",
                             "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git source snapshot failed")
    return result.stdout.strip()


def reference(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("source reference must be a nonempty relative file path")
    path = Path(value)
    if path.is_absolute() or any(p in ("..", ".git", ".gitattributes", ".gitignore", ".gitmodules") for p in (v.lower() for v in path.parts)) or str(path).casefold() in (".", MANIFEST):
        raise ValueError("unsafe or reserved source reference")
    return path.as_posix()


def snapshot(manifest, destination, previous=None, root=factory.ROOT):
    root, manifest = Path(root).resolve(), Path(manifest).absolute()
    destination = Path(destination).absolute()
    if manifest.is_symlink() or destination.is_symlink():
        raise ValueError("manifest and destination must not be symlinks")
    # Normalize host aliases such as macOS /var -> /private/var before applying
    # the workspace boundary. Only the resolved, ignored destination is written.
    manifest, destination = manifest.resolve(), destination.resolve()
    try:
        relative = destination.relative_to(root / "output")
    except ValueError:
        raise ValueError("source snapshots must stay inside this workspace's ignored output/")
    destination = factory.relative_path(root, "output/" + str(relative))
    if destination.exists():
        raise ValueError("destination must be new; use --previous and a new destination for updates")
    sources = factory.read(manifest).get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("manifest needs a nonempty sources list")
    entries, content = {}, {}
    for item in sources:
        ref = reference(item["reference"])
        if ref in entries:
            raise ValueError("duplicate source reference: " + ref)
        origin, kind = item.get("origin"), item.get("kind")
        if not isinstance(origin, str) or not origin.strip() or kind not in ("source", "extracted_text", "user_statement"):
            raise ValueError("each source needs an origin and a recognized kind")
        source = manifest.parent / item["path"]
        if source.is_symlink() or not source.is_file():
            raise ValueError("source must be a regular, non-symlinked file")
        content[ref] = source.read_bytes()
        entries[ref] = {"origin": origin, "kind": kind, "sha256": hashlib.sha256(content[ref]).hexdigest()}
        if kind == "extracted_text":
            entries[ref]["derived_from"] = reference(item["derived_from"])
    prior = {}
    if previous:
        previous = Path(previous).absolute()
        if previous.is_symlink() or not (previous / ".git").is_dir():
            raise ValueError("previous must be a local snapshot repository")
        previous = previous.resolve()
        previous_revision = git(previous, "rev-parse", "HEAD")
        prior_doc = json.loads(git(previous, "show", previous_revision + ":" + MANIFEST))
        if prior_doc.get("format") != "prospect-source-v1":
            raise ValueError("previous is not a Prospect source snapshot")
        prior = prior_doc["sources"]
    combined = {**prior, **entries}
    folded = [r.casefold() for r in combined]
    if len(folded) != len(set(folded)):
        raise ValueError("source references collide on a case-insensitive filesystem")
    for ref, entry in combined.items():
        reference(ref)
        if any(str(parent).casefold() in folded for parent in Path(ref).parents if str(parent) != "."):
            raise ValueError("source references conflict as file and directory")
        if entry["kind"] == "extracted_text":
            parent = entry.get("derived_from")
            if parent not in combined or combined[parent]["kind"] != "source":
                raise ValueError("extracted text must reference an imported original source")
            if parent in entries and ref not in entries:
                raise ValueError("replace the extraction when its original changes: " + ref)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".source-stage-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "repository"
        if previous:
            git(Path(temporary), "clone", "--no-hardlinks", str(previous), str(stage))
            git(stage, "checkout", "--detach", previous_revision)
            git(stage, "remote", "remove", "origin")
        else:
            stage.mkdir()
            git(stage, "init", "-q")
        for ref, blob in content.items():
            target = factory.relative_path(stage, ref)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        factory.write(stage / MANIFEST, {"format": "prospect-source-v1", "sources": combined})
        git(stage, "add", "--", MANIFEST, *content)
        git(stage, "commit", "--allow-empty", "-qm", "Snapshot supplied prospect messaging sources")
        revision = git(stage, "rev-parse", "HEAD")
        if destination.exists():
            raise ValueError("destination appeared during preparation; nothing was applied")
        stage.rename(destination)
    return {"source": str(destination), "revision": revision, "files": sorted(combined),
            "status": "source_only_not_approved", "manifest": MANIFEST}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(snapshot(args.manifest, args.destination, args.previous), indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({"verdict": "error", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
