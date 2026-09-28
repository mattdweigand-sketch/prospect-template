import _support
import json
import re
import unittest
from pathlib import Path

import yaml
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared" / "scripts"))
import common

ROOT = Path(__file__).resolve().parents[1]
SHARED = _support.SHARED


def icp_frontmatter():
    return yaml.safe_load((SHARED / "icp.md").read_text().split("---")[1])


POLICY_REF = re.compile(r"(?<![A-Za-z0-9_])policy\.((?!yaml\b)[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)")


def skill_read_keys():
    """Dotted policy keys the procedures in the workflow folders reference."""
    from test_skill_procedures import procedure_files
    keys = set()
    for f in procedure_files():
        keys.update(POLICY_REF.findall(f.read_text()))
    return keys


def strings(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)
    elif isinstance(x, str):
        yield x


class PolicyPathTests(unittest.TestCase):
    def test_talk_track_file_relative_to_shared_exists(self):
        pol = yaml.safe_load((SHARED / "policy.yaml").read_text())
        tt = pol["outreach"]["talk_track"]
        self.assertTrue((SHARED / tt["file"]).is_file())
        self.assertEqual(tt, {"file": "talk-track.md"})

    def test_no_orphan_policy_keys(self):
        """Every second-level policy key is read by a script (quoted key name in _shared/scripts/*.py or workflows/*/*.py) or referenced
        by a procedure in a workflow folder, itself or through a dotted child."""
        pol = yaml.safe_load((SHARED / "policy.yaml").read_text())
        listed = skill_read_keys()
        self.assertTrue(listed, "no procedure references a policy key, test is stale")
        scripts = list((ROOT / "_shared" / "scripts").glob("*.py")) + list((ROOT / "scripts").glob("*.py")) + list((ROOT / "workflows").glob("*/*.py"))
        code = "\n".join(p.read_text() for p in scripts)
        orphans = []
        for top, block in pol.items():
            if not isinstance(block, dict):
                continue
            for key in block:
                dotted = f"{top}.{key}"
                read = re.search(r"[\"']" + re.escape(key) + r"[\"':]", code) is not None
                covered = dotted in listed or any(k.startswith(dotted + ".") for k in listed)
                if not (read or covered):
                    orphans.append(dotted)
        self.assertEqual(orphans, [], f"policy keys no script reads and no procedure references: {orphans}")


    def test_reference_headers_hold_only_consumed_settings(self):
        icp = common.icp_frontmatter(SHARED)
        self.assertEqual(set(icp), {"territory", "verticals", "disqualifiers"})
        tax = common.load_taxonomy(SHARED)
        self.assertEqual(set(tax), {"tiers", "admission"})
        self.assertEqual(set(tax["admission"]), {"tier1_min", "tier2_min", "warehouse_needs_web_tier2", "warehouse_max_counted"})
        ids = []
        for tier, entries in tax["tiers"].items():
            for entry in entries:
                ids.append(entry["id"])
                self.assertTrue(set(entry) <= {"id", "freshness_days", "source"})
                if tier != "tier3": self.assertGreater(entry["freshness_days"], 0)
        self.assertEqual(len(ids), len(set(ids)))
        talk = common.load_talk_track(SHARED)
        self.assertEqual(set(talk["meta"]), {"review_by", "verify_before_action"})
        self.assertRegex(str(talk["meta"]["review_by"]), r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("## Claim boundaries", talk["body"])


if __name__ == "__main__":
    unittest.main()
