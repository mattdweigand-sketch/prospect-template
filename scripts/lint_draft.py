"""Configurable cold-email surface checks. Human review owns meaning and voice."""
import argparse
import json
import re
from pathlib import Path

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def check(body, rules):
    """Check the phrase list, formatting rules and limits configured in policy."""
    if not isinstance(body, str) or not body.strip():
        return ["body must be a nonempty string"]
    hits = []
    for phrase in rules["forbidden_phrases"]:
        if phrase.casefold() in body.casefold():
            hits.append("forbidden phrase: " + phrase)
    for mark in rules["forbidden_punctuation"]:
        if mark in body:
            hits.append("forbidden punctuation: " + mark)
    if len(re.findall(r"\b[\w']+\b", body)) > rules["max_body_words"]:
        hits.append("body exceeds configured word limit")
    if rules["no_emoji"] and EMOJI.search(body):
        hits.append("emoji in email")
    if rules["no_hashtags"] and re.search(r"(?<!\w)#\w+", body):
        hits.append("hashtag in email")
    if rules["no_markdown"] and ("**" in body or re.search(r"(?m)^\s*(?:[-*+]\s+|\d+\.\s+|#{1,6}\s+)", body)):
        hits.append("markdown formatting in email")
    return hits


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--body", required=True)
    ap.add_argument("--policy", default=str(Path(__file__).resolve().parents[1] / "_shared/policy.json"))
    args = ap.parse_args()
    try:
        hits = check(Path(args.body).read_text(), json.loads(Path(args.policy).read_text())["outreach"]["lint"])
        print(json.dumps({"verdict": "block" if hits else "allow", "hits": hits}))
        raise SystemExit(bool(hits))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"verdict": "error", "reason": str(exc)}))
        raise SystemExit(2)
