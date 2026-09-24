#!/usr/bin/env python3
"""Approval hashes for the three units an outreach packet rests on. Imported by outreach_gate.py and refresh_tracks.py.

A unit is hashed whole, minus its own approval stamp. The stamp is
{date: YYYY-MM-DD, sha: 12 hex}. A matching sha detects unchanged content;
it does not establish that approval happened. refresh_tracks.py prepares
proposed stamps in a separate directory. Applying them to active configuration
requires the exact review and authorization recorded through workflows/run.md.

Units
    row            a claims.json row. Stamp key: approved
    signal entry   a taxonomy.json tier1 or tier2 entry. Stamp key: approved
    persona_cares  the icp.md frontmatter persona_cares mapping. Stamp key: persona_cares_approved, next to it
"""
import hashlib
import json

STAMP_KEY = "approved"
PERSONA_STAMP_KEY = "persona_cares_approved"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def unit_hash(obj, exclude=(STAMP_KEY,)):
    if isinstance(obj, dict):
        obj = {k: v for k, v in obj.items() if k not in exclude}
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()[:12]


def stamp_current(unit, stamp):
    """True when stamp is {date, sha} and sha equals the unit's current hash."""
    return isinstance(stamp, dict) and bool(stamp.get("date")) and stamp.get("sha") == unit_hash(unit)


def make_stamp(unit, on):
    return {"date": str(on), "sha": unit_hash(unit)}
