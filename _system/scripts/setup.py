#!/usr/bin/env python3
"""Stage, review, and apply local configuration. No network or provider writes.

Commands: init RUN; prepare RUN; apply RUN --approval-reference REF.
Prepare binds full configuration, source revision, previews, and active preimages.
Apply records an actual user approval reference; a string is not proof of consent.
"""
import argparse
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import yaml
import setup_common as sc
from validate_setup import validate, require, text


def init(run_id, root=sc.ROOT):
    run = sc.run_path(root, run_id)
    require(not run.exists(), 'run already exists; choose a new id')
    active = sc.relative_path(root, '.local/config')
    source = active if active.is_dir() else sc.ROOT / 'setup/templates'
    sc.hashes(source)
    proposal = run / 'proposal'
    proposal.mkdir(parents=True)
    for name in sc.FILES:
        shutil.copyfile(source / name, proposal / name)
    # An inherited review is not review of this new proposal.
    p = yaml.safe_load((proposal / 'policy.yaml').read_text())
    p['deployment']['review_reference'] = None
    (proposal / 'policy.yaml').write_text(yaml.safe_dump(p, sort_keys=False))
    sc.write(run / 'previews.json', {name:{'scenario':'', 'decision':'', 'reason':'', 'draft':''} for name in ('clear_fit','indirect_fit','poor_fit')})
    return {'status':'staged_not_active','run':str(run),'proposal':str(proposal)}


def prepare(run_id, root=sc.ROOT):
    run = sc.run_path(root, run_id)
    proposal = sc.relative_path(run, 'proposal')
    result = validate(proposal, root)
    preview_path = sc.relative_path(run, 'previews.json')
    previews = sc.read(preview_path)
    require(set(previews) == {'clear_fit','indirect_fit','poor_fit'}, 'three synthetic fit previews are required')
    for name, preview in previews.items():
        require(all(text(preview.get(key)) for key in ('scenario','decision','reason')), name + ' needs scenario, decision and reasoning')
        require(preview['decision'] in ('draft','research','reject'), 'invalid preview decision')
        if preview['decision'] == 'draft': require(text(preview.get('draft')), 'draft preview needs actual wording')
    require(previews['clear_fit']['decision'] == 'draft' and previews['indirect_fit']['decision'] == 'research', 'clear-fit and indirect-fit previews must exercise drafting and research')
    require(previews['poor_fit']['decision'] == 'reject', 'poor-fit preview must reject outreach')
    active = sc.relative_path(root, '.local/config')
    pre = sc.hashes(active, missing=True)
    report = ['# Configuration review', '', 'Review these complete postimages and synthetic samples before approving. Mechanical validation does not establish source truth or business fit.', '']
    for name in sc.FILES:
        before = (active / name).read_text() if pre[name] else ''
        after = (proposal / name).read_text()
        report += ['## ' + name, '', '```diff', ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='active/'+name,tofile='proposal/'+name)).rstrip(), '```', '', '### Complete proposed file', '', '````', after.rstrip(), '````', '']
    report += ['## Synthetic previews', '', '```json', json.dumps(previews, indent=2), '```', '', 'Approval covers these exact files only. Provider availability and message meaning need separate review. Changed bytes require prepare and fresh approval.']
    if result['module_previews']:
        report += ['', '## Enabled optional-module previews', '', 'Review both greetings, fixed copy and adoption statements for the configured offer. These samples are rendered from the proposed policy, not generated outreach.', '', '```json', json.dumps(result['module_previews'], indent=2), '```']
    review_path = sc.relative_path(run, 'review.md')
    review_path.write_text('\n'.join(report) + '\n')
    receipt = {'schema_version':1,'run':run_id,'preimages':pre,'postimages':result['files'], 'previews_sha256':sc.digest(preview_path), 'review_sha256':sc.digest(review_path), 'source_revision':result['source_revision']}
    sc.write(sc.relative_path(run, 'review.json'), receipt)
    return {'status':'awaiting_exact_review', 'review':str(review_path), 'review_sha256':receipt['review_sha256']}


def apply(run_id, approval_reference, root=sc.ROOT):
    require(text(approval_reference), 'actual user approval reference required')
    run = sc.run_path(root, run_id)
    require(not (run / 'applied.json').exists(), 'this review was already applied')
    receipt_path = sc.relative_path(run, 'review.json')
    receipt = sc.read(receipt_path)
    proposal = sc.relative_path(run, 'proposal')
    active = sc.relative_path(root, '.local/config')
    require(receipt.get('schema_version') == 1 and receipt.get('run') == run_id, 'invalid review identity')
    require(sc.hashes(proposal) == receipt['postimages'], 'proposal changed; prepare and obtain new approval')
    require(sc.hashes(active, missing=True) == receipt['preimages'], 'active configuration changed; prepare and obtain new approval')
    require(sc.digest(sc.relative_path(run, 'review.md')) == receipt['review_sha256'], 'review changed; prepare and obtain new approval')
    require(sc.digest(sc.relative_path(run, 'previews.json')) == receipt['previews_sha256'], 'previews changed; prepare and obtain new approval')
    validate(proposal, root)
    active.parent.mkdir(parents=True, exist_ok=True)
    backup = sc.relative_path(run, 'previous-config')
    require(not backup.exists(), 'backup exists; inspect the earlier apply before proceeding')
    approval = {'schema_version':1,'run':run_id,'approval_reference':approval_reference,'files':receipt['postimages'],'review_sha256':receipt['review_sha256'],'applied_at':datetime.now(timezone.utc).isoformat()}
    # An exclusive lock prevents concurrent applies; a crash leaves it for inspection.
    lock = sc.relative_path(root, '.local/apply.lock')
    with lock.open('x'):
        try:
            with tempfile.TemporaryDirectory(prefix='.config-stage-', dir=active.parent) as temp:
                stage = Path(temp) / 'config'
                stage.mkdir()
                for name in sc.FILES: shutil.copyfile(proposal / name, stage / name)
                sc.write(stage / 'approval.json', approval)
                require(sc.hashes(stage) == receipt['postimages'], 'staged copy differs from review')
                require(sc.hashes(active, missing=True) == receipt['preimages'], 'active configuration changed during apply')
                existed = active.exists()
                if existed: active.rename(backup)
                try:
                    stage.rename(active)
                    require(sc.hashes(active) == receipt['postimages'], 'applied readback mismatch')
                except Exception:
                    if active.exists(): active.rename(run / 'failed-config')
                    if existed: backup.rename(active)
                    raise
            sc.write(run / 'applied.json', approval)
        finally:
            lock.unlink()
    return {'status':'applied','config':str(active),'approval_reference':approval_reference}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('init','prepare','apply'):
        child = sub.add_parser(command); child.add_argument('run')
        if command == 'apply': child.add_argument('--approval-reference', required=True)
    args = parser.parse_args()
    try:
        result = apply(args.run,args.approval_reference) if args.command == 'apply' else globals()[args.command](args.run)
        print(json.dumps(result, indent=2)); return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeError, yaml.YAMLError) as exc:
        print(json.dumps({'status':'blocked','reason':str(exc)})); return 1


if __name__ == '__main__':
    sys.exit(main())
