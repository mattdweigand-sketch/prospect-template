#!/usr/bin/env python3
"""Validate a complete staged configuration and its pinned source evidence. No provider calls.

This checks structure, dates, exact source quotes, and configuration consistency.
It cannot establish that sources are true, claims are appropriate, or review occurred.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo
import yaml
import setup_common as sc
sys.path.insert(0, str(sc.ROOT / '_shared' / 'scripts'))
import common
import provider_map


def require(value, message):
    if not value:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def shape(value, sample, path='policy'):
    if isinstance(sample, dict):
        require(isinstance(value, dict), path + ' must be an object')
        if path == 'policy.outreach.task_status_map':
            return
        for key, child in sample.items():
            require(key in value, path + '.' + key + ' is missing')
            shape(value[key], child, path + '.' + key)
    elif sample is not None:
        require(type(value) is type(sample), path + ' has the wrong type')


def validate(folder, root=sc.ROOT, today=None):
    folder, root = Path(folder), Path(root)
    sc.hashes(folder)
    p = yaml.safe_load((folder / 'policy.yaml').read_text())
    exemplar = yaml.safe_load((sc.ROOT / 'examples/config/policy.yaml').read_text())
    shape(p, exemplar)
    require(p['schema_version'] == 1, 'unsupported policy schema')
    deployment = p['deployment']
    require(deployment['mode'] == 'configured', 'fictional examples cannot become active configuration')
    for key in ('business_name', 'product_name', 'review_reference'):
        require(text(deployment[key]), 'deployment.' + key + ' needs an actual reviewed value')
    require(not any(marker in deployment['product_name'] + deployment['business_name'] for marker in ('Example Offer','Example Company')), 'replace the fictional business')
    ident = p['identity']
    require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', ident['owner_email']), 'identity.owner_email is invalid')
    require(not ident['owner_email'].endswith(('.test', '.invalid', '@example.com')), 'replace the fictional seller address')
    require(common.opaque_id(ident['crm_user_id']) and ident['crm_user_id'] != 'example-owner', 'replace the fictional CRM identity with your opaque native user ID')
    ZoneInfo(ident['timezone'])
    require(p['approval']['unattended_writes'] is False and p['approval']['readback_required'] is True, 'retain approval and readback boundaries')
    require({'send email', 'create deal', 'change deal stage or amount'} <= set(p['approval']['never']), 'retain prohibited writes')
    require(p['outreach']['max_drafts_per_run'] == 1 and p['followup']['max_tasks_per_run'] == 1, 'outreach and followup are single-proposal workflows')
    require(1 <= p['arr_growth']['max_accounts_per_run'] <= 2, 'ARR workflow supports at most two accounts')
    for section, keys in {'scan':['quote_min_words','max_signals_per_account'], 'outreach':['bundle_checked_max_age_hours','suppression_days','activity_lookback_days'], 'followup':['due_calendar_days','arr_growth_due_business_days'], 'prospector':['max_candidates_per_run','max_people_per_account']}.items():
        for key in keys:
            require(type(p[section][key]) is int and p[section][key] > 0, section + '.' + key + ' must be positive')
    require(p['outreach']['activity_lookback_days'] >= p['outreach']['suppression_days'], 'activity reads must cover suppression window')
    statuses = p['outreach']['task_status_map']
    require(bool(statuses) and all(text(k) and v in ('completed','open','cancelled') for k,v in statuses.items()), 'task_status_map must classify native statuses')
    require(statuses.get(p['followup']['task']['status']) == 'open', 'followup Task status must map to open')
    require(all(statuses.get(s) in ('completed','cancelled') for s in p['followup']['closed_statuses']), 'closed_statuses must agree with task_status_map')
    require(p['outreach']['talk_track']['file'] == 'talk-track.md' and p['email_voice']['file'] == 'voice.md', 'references must use canonical filenames')
    require(text(p['email_voice']['source_reference']), 'email voice needs a source_reference')
    require(p['retention']['operational_data'] == 'temporary_outside_checkout' and p['retention']['approval_record'] == 'chat_and_provider', 'retain operational data boundaries')
    require(text(p['retention']['review_reference']), 'record the reviewed retention preference')
    icp = common.icp_frontmatter(folder)
    territory = icp['territory']
    require(type(territory['min_employees']) is int and type(territory['max_employees']) is int and 0 < territory['min_employees'] <= territory['max_employees'], 'invalid employee territory range')
    taxonomy = common.load_taxonomy(folder)
    ids = []
    for tier, entries in taxonomy['tiers'].items():
        require(tier in ('tier1','tier2','tier3') and isinstance(entries,list), 'invalid signal tier')
        for entry in entries:
            require(text(entry.get('id')), 'signal id required')
            ids.append(entry['id'])
            if tier != 'tier3':
                require(type(entry.get('freshness_days')) is int and entry['freshness_days'] > 0, 'signal freshness must be positive')
    require(len(ids) == len(set(ids)), 'duplicate signal ids')
    admission = taxonomy['admission']
    require(all(type(admission[k]) is int and admission[k] > 0 for k in ('tier1_min','tier2_min','warehouse_max_counted')), 'invalid signal admission counts')
    require(type(admission['warehouse_needs_web_tier2']) is bool, 'warehouse pairing flag must be boolean')
    track = common.load_talk_track(folder)
    require(date.fromisoformat(str(track['meta']['review_by'])) >= (today or common.policy_today(p)), 'talk track is past its review date')
    require(track['meta']['verify_before_action'] is True, 'retain verification of volatile capability claims')
    require('## Claim boundaries' in track['body'], 'talk track must explain claim boundaries')
    sources = sc.read(folder / 'sources.json')
    require(sources.get('schema_version') == 1, 'unsupported source schema')
    watch = sources.get('watch_paths')
    require(isinstance(watch,list) and watch and len(watch) == len(set(watch)), 'source watch_paths must be nonempty and unique')
    blobs = {ref:sc.source_blob(sources, ref, root) for ref in watch}
    if sc.source_root(sources,root).is_relative_to(root.resolve() / '.local/sources'):
        require(p['retention']['setup_sources_permitted'] is True, 'snapshot retention must be explicitly permitted')
    claims = sources.get('claims')
    require(isinstance(claims,list) and claims, 'record supported messaging assertions in sources.json')
    for claim in claims:
        for key in ('text','path','quote','kind','attribution','limitations'):
            require(text(claim.get(key)), 'claim needs ' + key)
        require(claim['kind'] in ('source','extracted_text','user_statement'), 'unsupported claim kind')
        require(type(claim.get('public_naming')) is bool, 'claim needs explicit public_naming permission')
        require(claim['text'] in track['body'], 'claim text is absent from the talk track')
        require(claim['path'] in blobs, 'claim source must be watched')
        require(claim['quote'] in blobs[claim['path']].decode('utf-8'), 'claim quote is absent from the pinned source')
    voice_ref = p['email_voice']['source_reference']
    require(voice_ref in blobs, 'voice source must be watched')
    voice = (folder / 'voice.md').read_text().strip()
    require(len(voice.split()) >= 10, 'voice.md needs a substantive approved sample')
    require(voice in blobs[voice_ref].decode('utf-8'), 'voice sample must occur in its pinned source')
    contradiction = sources.get('contradictions_path')
    if contradiction:
        require(contradiction in blobs, 'contradiction register must be watched')
    providers = yaml.safe_load((folder / 'providers.yaml').read_text())
    require(providers.get('schema_version') == 1, 'unsupported provider schema')
    expected = yaml.safe_load((sc.ROOT / 'examples/config/providers.yaml').read_text())['capabilities']
    require(set(providers.get('capabilities',{})) == set(expected), 'provider capability catalog differs from the contract')
    for name, cap in providers['capabilities'].items():
        require(isinstance(cap,dict) and set(cap) == set(expected[name]), 'invalid provider mapping: ' + name)
        if cap['tool'] is not None:
            require(all(text(v) for v in cap.values()), 'incomplete provider mapping: ' + name)
        else:
            require(all(v is None for v in cap.values()), 'unavailable capability must be entirely null: ' + name)
    provider_map.validate_catalog(providers)
    enabled = p['user_scan']['enabled'] or p['arr_growth']['enabled'] or p['prospector']['adoption_source']['enabled']
    require(not enabled or p['warehouse']['enabled'], 'adoption and ARR modules require an enabled warehouse')
    if p['warehouse']['enabled']:
        require(text(p['warehouse']['name']), 'warehouse name required')
    required_queries = []
    if p['user_scan']['enabled']: required_queries.append('adoption_lookup')
    if p['prospector']['adoption_source']['enabled']: required_queries.append('adoption_territory')
    if p['arr_growth']['enabled']: required_queries.append('arr_growth_source')
    for name in required_queries:
        query = p['warehouse']['queries'][name]
        require(text(query.get('path')) and query['path'].startswith('.local/queries/'), 'query must be a reviewed private copy')
        path = sc.relative_path(root, query['path'])
        require(path.is_file() and sc.digest(path) == query.get('sha256'), 'query hash mismatch: ' + name)
        require('prospect_source.' not in path.read_text(), 'map the fictional SQL interface before enabling it')
    return {'status':'valid_configuration_not_approval', 'files':sc.hashes(folder), 'source_revision':sources['revision'], 'claims_checked':len(claims)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.config), indent=2)); return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeError, yaml.YAMLError) as exc:
        print(json.dumps({'status':'blocked','reason':str(exc)})); return 1


if __name__ == '__main__':
    sys.exit(main())
