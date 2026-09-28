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
sys.path.insert(0, str(sc.ROOT / "_system" / "scripts"))
import common
import provider_map
import policy_templates as templates


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
        if isinstance(sample, str):
            require(text(value), path + ' must be nonblank')
        if isinstance(sample, list):
            require(all(text(item) for item in value), path + ' must contain nonblank strings')


def validate_structure(folder):
    """Check all installed file contracts without reading external dependencies."""
    folder = Path(folder)
    p = yaml.safe_load((folder / 'policy.yaml').read_text())
    exemplar = yaml.safe_load((sc.ROOT / 'setup/templates/policy.yaml').read_text())
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
    for section, keys in {'scan':['quote_min_words','max_signals_per_account'], 'outreach':['bundle_checked_max_age_hours','suppression_days','activity_lookback_days'], 'followup':['due_calendar_days','arr_growth_due_business_days'], 'prospector':['max_candidates_per_run','max_people_per_account'], 'arr_growth':['window_days','candidate_rows','suppression_days']}.items():
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
    require(p['outreach']['lint']['max_body_words'] > 0, 'lint max_body_words must be positive')
    require(p['prospector']['adoption_source']['candidate_rows'] > 0, 'adoption candidate_rows must be positive')
    require(p['outreach']['suppressing_task_subtypes'] and p['outreach']['recipient_sources'], 'outreach source and subtype lists must be nonempty')
    require(p['user_scan']['bundle_keys'] == exemplar['user_scan']['bundle_keys'], 'user_scan.bundle_keys must match the supported record contract')
    require(sorted(p['user_scan']['adoption_values']) == sorted(exemplar['user_scan']['adoption_values']), 'unsupported adoption values')
    templates.render(p['followup']['task']['subject'], email_subject='Synthetic subject')
    templates.followup_description(p['followup']['task']['description'], 'synthetic-message', 'synthetic-thread', 'synthetic-signal', 'Synthetic angle')
    icp = common.icp_frontmatter(folder)
    require(isinstance(icp, dict), 'ICP frontmatter must be an object')
    territory = icp.get('territory')
    require(isinstance(territory, dict) and type(territory.get('min_employees')) is int and type(territory.get('max_employees')) is int and 0 < territory['min_employees'] <= territory['max_employees'], 'invalid employee territory range')
    verticals = icp.get('verticals')
    require(isinstance(verticals, list), 'ICP verticals must be a list (empty means no ranked preference)')
    vertical_ids = []
    for entry in verticals:
        require(isinstance(entry, dict) and text(entry.get('id')), 'vertical id required')
        require(type(entry.get('rank')) is int and entry['rank'] > 0, 'vertical rank must be a positive integer')
        vertical_ids.append(entry['id'])
    require(len(vertical_ids) == len(set(vertical_ids)), 'duplicate vertical ids')
    disqualifiers = icp.get('disqualifiers')
    require(isinstance(disqualifiers, dict), 'ICP disqualifiers must be an object')
    disqualifier_ids = []
    for category in ('hard', 'recoverable'):
        entries = disqualifiers.get(category)
        require(isinstance(entries, list) and all(text(v) for v in entries), 'disqualifiers.' + category + ' must be a list of nonblank ids')
        disqualifier_ids.extend(entries)
    require(len(disqualifier_ids) == len(set(disqualifier_ids)), 'duplicate or conflicting disqualifier ids')
    taxonomy = common.load_taxonomy(folder)
    require(isinstance(taxonomy, dict) and isinstance(taxonomy.get('tiers'), dict) and set(taxonomy['tiers']) == {'tier1','tier2','tier3'}, 'signal tiers must include exactly tier1, tier2 and tier3')
    ids = []
    for tier, entries in taxonomy['tiers'].items():
        require(isinstance(entries, list), 'invalid signal tier')
        for entry in entries:
            require(isinstance(entry, dict) and text(entry.get('id')), 'signal id required')
            ids.append(entry['id'])
            if tier != 'tier3' or 'freshness_days' in entry:
                require(type(entry.get('freshness_days')) is int and entry['freshness_days'] > 0, 'signal freshness must be positive')
            if 'source' in entry:
                require(text(entry['source']), 'signal source must be a nonblank reference')
    require(len(ids) == len(set(ids)), 'duplicate signal ids')
    admission = taxonomy.get('admission')
    require(isinstance(admission, dict) and all(type(admission.get(k)) is int and admission[k] > 0 for k in ('tier1_min','tier2_min','warehouse_max_counted')), 'invalid signal admission counts')
    require(type(admission.get('warehouse_needs_web_tier2')) is bool, 'warehouse pairing flag must be boolean')
    if p['prospector']['adoption_source']['enabled']:
        entry, tier = common.taxonomy_entry(taxonomy, p['prospector']['adoption_source']['signal_type'])
        require(entry and tier == 'tier2' and entry.get('source'), 'adoption signal_type must name a counted warehouse signal')
    providers = yaml.safe_load((folder / 'providers.yaml').read_text())
    require(providers.get('schema_version') == 1, 'unsupported provider schema')
    expected = yaml.safe_load((sc.ROOT / 'setup/templates/providers.yaml').read_text())['capabilities']
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
    return p


def validate_module_copy(p, workflow=None):
    sections = []
    if p['user_scan']['enabled'] and workflow in (None, 'signal-user-scan'):
        sections.append(p['user_scan']['statements'])
    if p['arr_growth']['enabled'] and workflow in (None, 'signal-arr-growth'):
        sections.append(p['arr_growth']['draft'])
    for section in sections:
        for value in section.values():
            require(not re.search(r'example (?:offer|company)|^\s*Seller\s*$', value, re.I | re.M), 'replace fictional copy in enabled optional modules')
    return templates.module_previews(p, workflow)


def validate_messaging(folder, root, p, today=None):
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
    return sources, claims


def validate_queries(p, root, workflow=None):
    """Setup checks all enabled queries; runtime checks the selected workflow only."""
    required_queries = []
    if p['user_scan']['enabled'] and workflow in (None, 'signal-user-scan'): required_queries.append('adoption_lookup')
    if p['prospector']['adoption_source']['enabled'] and workflow in (None, 'signal-prospector'): required_queries.append('adoption_territory')
    if p['arr_growth']['enabled'] and workflow in (None, 'signal-arr-growth'): required_queries.append('arr_growth_source')
    for name in required_queries:
        query = p['warehouse']['queries'][name]
        require(text(query.get('path')) and query['path'].startswith('.local/queries/'), 'query must be a reviewed private copy')
        path = sc.relative_path(root, query['path'])
        require(path.is_file() and sc.digest(path) == query.get('sha256'), 'query hash mismatch: ' + name)
        require('prospect_source.' not in path.read_text(), 'map the fictional SQL interface before enabling it')


def validate(folder, root=sc.ROOT, today=None):
    folder, root = Path(folder), Path(root)
    files = sc.hashes(folder)
    p = validate_structure(folder)
    sources, claims = validate_messaging(folder, root, p, today)
    validate_queries(p, root)
    previews = validate_module_copy(p)
    return {'status':'valid_configuration_not_approval', 'files':files, 'source_revision':sources['revision'], 'claims_checked':len(claims), 'module_previews':previews}


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
