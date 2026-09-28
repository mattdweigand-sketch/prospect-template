#!/usr/bin/env python3
"""Compare watched source blobs against a full commit hash; optionally stage a refresh.

Never applies or approves changes. A new revision with unchanged wording still needs review.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import yaml
import setup_common as sc
import setup
from validate_setup import require


def inspect(revision, root=sc.ROOT):
    require(re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', revision or ''), 'provide a full commit hash')
    config = sc.relative_path(root,'.local/config')
    doc = sc.read(config / 'sources.json')
    receipt = sc.read(config / 'approval.json')
    require(sc.hashes(config) == receipt.get('files'), 'active configuration changed after approval')
    repo = sc.source_root(doc,root)
    require(sc.git(repo,'rev-parse','--verify',revision+'^{commit}').decode().strip() == revision, 'revision must resolve exactly')
    target={**doc,'revision':revision}
    changed=[]
    for path in doc['watch_paths']:
        before=sc.source_blob(doc,path,root)
        try: after=sc.source_blob(target,path,root)
        except ValueError:
            changed.append({'path':path,'status':'missing_or_nonregular'}); continue
        if before != after: changed.append({'path':path,'status':'changed'})
    return {'status':'review_required', 'baseline':doc['revision'], 'target':revision,'changed':changed,'limit':'Watch coverage and semantic contradictions require human review; no source change auto-updates messaging.'}


def stage(revision, run_id, root=sc.ROOT):
    report=inspect(revision,root)
    result=setup.init(run_id,root)
    run=sc.run_path(root,run_id)
    doc=sc.read(run/'proposal/sources.json'); doc['revision']=revision
    sc.write(run/'proposal/sources.json',doc)
    sc.write(run/'source-changes.json',report)
    return {**report, **result}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True); parser.add_argument('--stage-run')
    args=parser.parse_args()
    try:
        result=stage(args.revision,args.stage_run) if args.stage_run else inspect(args.revision)
        print(json.dumps(result,indent=2)); return 0
    except (OSError,ValueError,TypeError,KeyError,AttributeError,yaml.YAMLError) as exc:
        print(json.dumps({'status':'blocked','reason':str(exc)})); return 1


if __name__ == '__main__': sys.exit(main())
