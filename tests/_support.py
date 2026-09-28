"""Explicit synthetic configuration for tests only; never imported by production."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "examples" / "config"
os.environ["PROSPECT_CONFIG_DIR"] = str(SHARED)
