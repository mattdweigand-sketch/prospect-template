#!/usr/bin/env python3
"""Advisory style review. Never grants or blocks authorization."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'_shared/scripts'))
import common


def lint(body,policy):
    settings=policy['outreach']['lint']
    if not settings['enabled']: return []
    flags=[]
    if len(body.split()) > settings['max_body_words']: flags.append('body exceeds configured word target')
    flags += ['review phrase: '+phrase for phrase in settings['phrases'] if phrase.lower() in body.lower()]
    if body.count('?') != 1: flags.append('review the number of questions')
    return flags


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--body',type=Path,required=True)
    args=parser.parse_args()
    try:
        print(json.dumps({'advisory':lint(args.body.read_text(),common.load_policy())})); return 0
    except common.INPUT_ERRORS as exc:
        print(common.error_json(exc)); return 2


if __name__ == '__main__': sys.exit(main())
