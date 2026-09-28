#!/usr/bin/env python3
"""Check approved local configuration and declared capabilities. Does not prove live access."""
import argparse
import json
from pathlib import Path
import sys
import yaml
import setup_common as sc
from validate_setup import validate, require

CAPABILITIES = {
 'signal-scan': ['web.search','web.fetch','salesforce.query'],
 'signal-prospector': ['web.search','web.fetch','salesforce.query'],
 'signal-outreach': ['salesforce.query','gmail.search','gmail.read_message','gmail.create_draft','gmail.read_draft'],
 'signal-followup': ['salesforce.query','salesforce.create_task','salesforce.readback','gmail.search','gmail.read_message'],
 'signal-user-scan': ['salesforce.query','warehouse.query','warehouse.status','warehouse.results'],
 'signal-arr-growth': ['salesforce.query','gmail.search','gmail.read_message','gmail.create_draft','gmail.read_draft','warehouse.query','warehouse.status','warehouse.results'],
}


def check(workflow, root=sc.ROOT):
    config = sc.relative_path(root, '.local/config')
    result = validate(config,root)
    receipt = sc.read(sc.relative_path(config,'approval.json'))
    require(receipt.get('schema_version') == 1 and receipt.get('approval_reference'), 'configuration needs an application receipt')
    require(result['files'] == receipt.get('files'), 'active configuration changed after approval; run setup or refresh')
    policy = yaml.safe_load((config / 'policy.yaml').read_text())
    module = {'signal-user-scan':'user_scan', 'signal-arr-growth':'arr_growth'}.get(workflow)
    require(not module or policy[module]['enabled'], 'optional workflow is disabled; configure it through setup')
    caps = yaml.safe_load((config / 'providers.yaml').read_text())['capabilities']
    required = list(CAPABILITIES[workflow])
    if workflow == 'signal-prospector' and policy['prospector']['adoption_source']['enabled']:
        required += ['warehouse.query','warehouse.status','warehouse.results']
    missing = [name for name in required if not caps[name]['tool']]
    conditional = ['salesforce.create_account','salesforce.update_owner','salesforce.create_contact','salesforce.readback','enrichment.verified_contact'] if workflow == 'signal-prospector' else []
    conditional_missing = [name for name in conditional if not caps[name]['tool']]
    return {'status':'missing_provider_mappings' if missing else 'configured_needs_live_reads', 'workflow':workflow, 'missing':missing, 'conditional_missing':conditional_missing, 'limit':'Tool discovery and complete authorized live reads are still required. Mappings and receipts are not proof of provider access or human consent.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('workflow',choices=CAPABILITIES)
    args = parser.parse_args()
    try:
        result=check(args.workflow); print(json.dumps(result,indent=2)); return 1 if result['missing'] else 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeError, yaml.YAMLError) as exc:
        print(json.dumps({'status':'blocked','reason':str(exc)})); return 1


if __name__ == '__main__': sys.exit(main())
