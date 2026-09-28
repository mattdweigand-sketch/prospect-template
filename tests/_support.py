"""Explicit synthetic configuration. Never imported by production tools."""
import atexit
import os
from pathlib import Path
import shutil
import tempfile
import yaml
ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "config"
_fixture = tempfile.TemporaryDirectory(prefix="prospect-test-config-")
atexit.register(_fixture.cleanup)
SHARED = Path(_fixture.name).resolve()
for file in EXAMPLES.iterdir():
    if file.is_file(): shutil.copyfile(file, SHARED / file.name)
policy = yaml.safe_load((SHARED / "policy.yaml").read_text())
policy["identity"]["timezone"] = "America/Los_Angeles"
policy["crm"]["house_owner_ids"] = ["005000000000002AAA", "005000000000003AAA"]
policy["scan"]["warm_engagement"]["ignored_owner_ids"] = ["005000000000004AAA"]
(SHARED / "policy.yaml").write_text("# Dropped orgs are not reported; synthetic optional ARR contract.\n" + yaml.safe_dump(policy, sort_keys=False))
os.environ["PROSPECT_CONFIG_DIR"] = str(SHARED)
