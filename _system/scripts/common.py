"""Shared helpers for _system/scripts. Imported by every gate. No CLI.

One home for the policy loader, the icp.md frontmatter parser, the talk-track.md loader, the policy clock,
ISO parsing, the taxonomy tier walk, and the error envelope. Behavior that used to be copied into each script lives here.
"""
import json
import os
import re
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[2]
SHARED = Path(os.environ.get("PROSPECT_CONFIG_DIR", ROOT / ".local" / "config")).resolve()
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def load_policy(shared=SHARED):
    return yaml.safe_load((Path(shared) / "policy.yaml").read_text())


def markdown_document(path):
    """One Markdown document: script settings in frontmatter, prose for the agent."""
    text = Path(path).read_text()
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"{Path(path).name} has no frontmatter block")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be a mapping")
    body = text[match.end():].strip()
    if not body:
        raise ValueError("Markdown body is empty")
    return {"meta": meta, "body": body}


def icp_frontmatter(shared=SHARED):
    return markdown_document(Path(shared) / "icp.md")["meta"]


def load_taxonomy(shared=SHARED):
    return markdown_document(Path(shared) / "signals.md")["meta"]


def load_talk_track(shared=SHARED):
    return markdown_document(Path(shared) / "talk-track.md")


def taxonomy_entry(tax, signal_type):
    """tier1 or tier2 entry with the id, plus its tier name. (None, None) when absent."""
    for tier in ("tier1", "tier2"):
        for t in tax["tiers"][tier]:
            if t["id"] == signal_type:
                return t, tier
    return None, None


def taxonomy_types(tax):
    """{id: {tier, freshness_days, source}} across every tier. evidence_gate.py and route_candidate.py read it."""
    return {e["id"]: {"tier": tier, "freshness_days": e.get("freshness_days"), "source": e.get("source")}
            for tier, entries in tax["tiers"].items() for e in entries}


def policy_tz(policy):
    return ZoneInfo(policy["identity"]["timezone"])


def policy_now(policy):
    return datetime.now(policy_tz(policy))


def policy_today(policy):
    return policy_now(policy).date()


def parse_iso(s, policy=None):
    """Aware datetime from an ISO string. 'Z' accepted. A bare date is noon in the policy timezone
    when policy is given, else None. A naive timestamp returns None."""
    if not isinstance(s, str) or not s.strip():
        return None
    s = s.strip().replace("Z", "+00:00")
    if len(s) <= 10:
        if policy is None:
            return None
        return datetime.combine(date.fromisoformat(s), time(12, 0), tzinfo=policy_tz(policy))
    try:
        t = datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo is not None else None


def error_json(exc):
    """Exit-2 envelope every gate prints. Same shape everywhere."""
    return json.dumps({"verdict": "error", "reason": f"{type(exc).__name__}: {exc}"})


INPUT_ERRORS = (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError, json.JSONDecodeError)


def opaque_id(value):
    """Nonempty, unpadded text without control characters; never infer provider or case-fold."""
    return (isinstance(value, str) and bool(value) and value == value.strip()
            and all(ord(c) >= 32 and ord(c) != 127 for c in value))
