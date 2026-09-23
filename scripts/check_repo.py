#!/usr/bin/env python3
"""Read-only checks for the portable factory and generated pointers."""
import json
from pathlib import Path
import re
import subprocess
import sys

from wrappers import ROOT, load_routes, render

PRIVATE = {"_shared/policy.json", "_shared/adapters.md", "_shared/icp.md", "_shared/taxonomy.json", "_shared/claims.json"}


def public_files(root):
    if (root / ".git").is_dir():
        proc = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root, capture_output=True, check=True)
        return sorted({Path(p) for p in proc.stdout.decode().split("\0") if p})
    return sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file()
                  and not any(x in (".git", "output", "__pycache__", ".venv") for x in p.relative_to(root).parts)
                  and str(p.relative_to(root)) not in PRIVATE)


def check(root=ROOT):
    errors = render(root, check=True)
    routes = load_routes(root)
    if len((root / "AGENTS.md").read_text().splitlines()) >= 60:
        errors.append("AGENTS.md should stay below 60 lines")
    contracts = {"workflows", "_shared", "_templates", "_templates/run", "setup", "scripts", "tests", "examples"}
    contracts |= {str(Path(r["workspace"]).parent) for r in routes.values()}
    for folder in contracts:
        if not (root / folder / "CONTEXT.md").is_file():
            errors.append("missing folder contract: " + folder)
    for name, row in routes.items():
        text = (root / row["workflow"]).read_text()
        for heading in ("## Load / Skip", "## Process", "## Outputs and readiness", "## Human check"):
            if heading not in text:
                errors.append(name + " missing " + heading)
    files = public_files(root)
    for rel in files:
        path = root / rel
        if path.is_symlink():
            errors.append("public template contains a symlink: " + str(rel))
            continue
        if str(rel) in PRIVATE or "output" in rel.parts or rel.name.startswith(".env"):
            errors.append("deployment or runtime material included: " + str(rel))
            continue
        if path.suffix not in (".md", ".json", ".py", ".txt", ".yml"):
            continue
        text = path.read_text()
        if path.suffix == ".json":
            try:
                json.loads(text)
            except ValueError as exc:
                errors.append(str(rel) + ": " + str(exc))
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                target = target.split("#")[0]
                if "{" not in target and not (path.parent / target).exists():
                    errors.append(f"broken link in {rel}: {target}")
        for address in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text):
            domain = address.split("@")[1]
            if domain not in ("example.com", "example.org", "example.net"):
                errors.append(f"non-example email in {rel}")
        if re.search(r"\b(?:005|001|003|006)[a-zA-Z0-9]{12}(?:[a-zA-Z0-9]{3})?\b", text):
            errors.append("CRM identifier in " + str(rel))
        if re.search(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----", text):
            errors.append("private key in " + str(rel))
        if re.search(r"/(?:Users|home)/[a-zA-Z0-9._-]+/", text):
            errors.append("personal filesystem path in " + str(rel))
    return errors, len(files)


if __name__ == "__main__":
    try:
        errors, count = check()
        print("\n".join(errors) if errors else f"PASS: {len(load_routes())} workflow routes; {count} public files; links, wrappers and template checks.")
        sys.exit(bool(errors))
    except (ValueError, OSError, TypeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
