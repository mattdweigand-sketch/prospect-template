"""Every procedure file in the workflow folders names only things that exist.

A saved project skill points to `workflows/<name>/CONTEXT.md` and `procedure.md`. This test resolves what
those procedure files reference: every `policy.<dotted>` key against policy.yaml, each explicit tool/reference path
against the checkout, and every named script against the workflow and shared tools. A procedure that
names a key or file that is not there fails here instead of at run time.
"""
import _support
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SHARED = _support.SHARED
EXPECTED_WORKFLOWS = {
    "signal-prospector", "signal-scan", "signal-user-scan",
    "signal-outreach", "signal-followup", "signal-arr-growth", "prospect-setup", "signal-refresh",
}


def procedure_files():
    """Executable procedures only; the blank starter is not a workflow."""
    return sorted((ROOT / "workflows").glob("*/procedure.md"))


def body_after_frontmatter(text):
    if text.startswith("---\n"):
        return text.split("---\n", 2)[2].lstrip("\n")
    return text

POLICY_REF = re.compile(r"(?<![A-Za-z0-9_])policy\.((?!yaml\b)[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)")
REPO_PATH = re.compile(r"(?<![A-Za-z0-9_./-])((?:_shared|workflows)/[A-Za-z0-9_./-]+)")
SCRIPT_NAME = re.compile(r"\b([a-z_]+\.(?:py|sql))\b")
SKILL_NAME = re.compile(r"`(signal-[a-z-]+)`")


def resolve(pol, dotted):
    node = pol
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


class SkillProcedureTests(unittest.TestCase):
    def setUp(self):
        self.pol = yaml.safe_load((SHARED / "policy.yaml").read_text())
        self.files = procedure_files()
        self.assertEqual({f.parent.name for f in self.files}, EXPECTED_WORKFLOWS)
        self.assertEqual({p.name for p in (ROOT / "workflows").iterdir() if p.is_dir()}, EXPECTED_WORKFLOWS)

    def test_title_matches_workflow(self):
        for f in self.files:
            self.assertEqual(body_after_frontmatter(f.read_text()).splitlines()[0], f"# {f.parent.name}", str(f))

    def test_policy_keys_resolve(self):
        missing = []
        for f in self.files:
            for dotted in sorted(set(POLICY_REF.findall(f.read_text()))):
                if not resolve(self.pol, dotted):
                    missing.append(f"{f.name}: policy.{dotted}")
        self.assertEqual(missing, [], f"procedure names policy keys absent from policy.yaml: {missing}")

    def test_explicit_repo_paths_exist(self):
        missing = []
        for f in self.files:
            for p in sorted(set(REPO_PATH.findall(f.read_text()))):
                if not (ROOT / p).exists():
                    missing.append(f"{f.name}: {p}")
        self.assertEqual(missing, [], f"procedure names files that do not exist: {missing}")

    def test_named_scripts_exist(self):
        missing = []
        for f in self.files:
            present = {p.name for folder in (ROOT / "_shared" / "scripts", ROOT / "scripts", f.parent) for p in folder.iterdir() if p.is_file()}
            for s in sorted(set(SCRIPT_NAME.findall(f.read_text()))):
                if s not in present:
                    missing.append(f"{f.name}: {s}")
        self.assertEqual(missing, [], f"procedure names scripts absent from its workflow or shared tools: {missing}")

    def test_frontmatter_workflow_matches_folder(self):
        for f in self.files:
            text = f.read_text()
            self.assertTrue(text.startswith("---\n"), f"{f.name} has no frontmatter")
            fm = yaml.safe_load(text.split("---\n", 2)[1])
            self.assertEqual(fm.get("workflow"), f.parent.name, str(f))
            self.assertNotIn("stage", fm)
            for key in ("reads", "writes", "next"):
                self.assertIn(key, fm, f"{f.name} frontmatter lacks {key}")

    def test_agents_routes_to_real_procedure_paths(self):
        agents = (ROOT / "AGENTS.md").read_text()
        for f in self.files:
            rel = f.relative_to(ROOT).as_posix()
            self.assertIn(f"`{rel}`", agents, f"AGENTS.md does not route to {rel}")

    def test_named_skills_are_routed(self):
        """Every sibling skill a procedure hands off to appears in the AGENTS.md route table."""
        agents = (ROOT / "AGENTS.md").read_text()
        unrouted = []
        for f in self.files:
            for s in sorted(set(SKILL_NAME.findall(f.read_text()))):
                if f"`{s}`" not in agents:
                    unrouted.append(f"{f.name}: {s}")
        self.assertEqual(unrouted, [], f"procedure hands off to skills AGENTS.md does not route: {unrouted}")

    def test_contract_inputs_and_handoffs_resolve(self):
        for procedure in self.files:
            contract = procedure.with_name("CONTEXT.md")
            self.assertTrue(contract.is_file(), str(contract))
            text = contract.read_text()
            for heading in ("## Inputs", "## Process", "## Output", "## Human check", "## Next"):
                self.assertIn(heading, text, str(contract))
            for target in re.findall(r"`([^`]+)`", text):
                if target.startswith("../") or target.endswith((".md", ".py", ".sql", ".yaml")):
                    resolved = (contract.parent / target).resolve()
                    self.assertIn(ROOT, resolved.parents, f"contract escapes repo: {target}")
                    if resolved.is_relative_to(ROOT / ".local/config"):
                        resolved = SHARED / resolved.relative_to(ROOT / ".local/config")
                    self.assertTrue(resolved.exists(), f"{contract}: {target}")
