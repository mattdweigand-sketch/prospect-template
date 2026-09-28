#!/usr/bin/env python3
"""Map one native record to canonical fields, or canonical fields to a native payload.

No provider calls. JSON pointers select object keys or array positions. Transformations
are explicit, never inferred. Missing fields, unknown enum values, dropped write fields
and overlapping write paths fail. This does not parse MIME, authenticate responses,
execute queries, or authorize writes. See shared/providers.md.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import sys
import yaml
import common

ACCOUNT = {'name', 'website', 'owner_id', 'headcount'}
CONTACT = {'first_name', 'last_name', 'title', 'email', 'account_id'}
TASK = {'subject', 'account_id', 'contact_id', 'owner_id', 'status', 'priority', 'subtype', 'due_date', 'description'}
EMAIL = {'to', 'subject', 'body', 'cc', 'bcc'}
CONTRACTS = {
    'crm.account.read': ACCOUNT | {'id', 'owner_is_active'},
    'crm.account.write': ACCOUNT,
    'crm.owner.write': {'owner_id'},
    'crm.contact.read': CONTACT | {'id'},
    'crm.contact.write': CONTACT,
    'crm.task.read': TASK | {'id'},
    'crm.task.write': TASK,
    'email.message.read': EMAIL | {'message_id', 'sent_at', 'is_sent'},
    'email.draft.read': EMAIL | {'id'},
    'email.draft.write': EMAIL,
}
OPTIONAL = {'email.message.read': {'thread_id'}, 'email.draft.read': {'message_id'}}
CAPABILITY_RECORDS = {
    'crm.query': ['crm.account.read', 'crm.contact.read', 'crm.task.read'],
    'crm.create_account': ['crm.account.write', 'crm.account.read'],
    'crm.update_owner': ['crm.owner.write', 'crm.account.read'],
    'crm.create_contact': ['crm.contact.write', 'crm.contact.read'],
    'crm.create_task': ['crm.task.write', 'crm.task.read'],
    'crm.readback': ['crm.account.read', 'crm.contact.read', 'crm.task.read'],
    'email.read_message': ['email.message.read'],
    'email.create_draft': ['email.draft.write', 'email.draft.read'],
    'email.read_draft': ['email.draft.read'],
}


def tokens(pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/') or re.search(r'~(?![01])', pointer):
        raise ValueError('mapping path must be a nonempty JSON pointer')
    return [part.replace('~1', '/').replace('~0', '~') for part in pointer[1:].split('/')]


def validate_mapping(name, mapping):
    if name not in CONTRACTS or not isinstance(mapping, dict):
        raise ValueError('unknown record or invalid mapping: ' + name)
    if not CONTRACTS[name] <= set(mapping) or set(mapping) - CONTRACTS[name] - OPTIONAL.get(name, set()):
        raise ValueError('mapping fields differ from record contract: ' + name)
    paths = []
    for field, spec in mapping.items():
        if not isinstance(spec, dict) or not {'path'} <= set(spec) or set(spec) - {'path', 'convert', 'values'}:
            raise ValueError('invalid field mapping: ' + field)
        path = tokens(spec['path'])
        paths.append(path)
        if spec.get('convert', 'identity') not in ('identity', 'id_string', 'integer'):
            raise ValueError('unsupported conversion: ' + field)
        if 'values' in spec:
            values = spec['values']
            if not isinstance(values, list) or not values:
                raise ValueError('values must be a nonempty list')
            seen = []
            for pair in values:
                if not isinstance(pair, dict) or set(pair) != {'from', 'to'}:
                    raise ValueError('enum entry needs from and to')
                if any(equal(pair['from'], prior) for prior in seen):
                    raise ValueError('duplicate enum input')
                seen.append(pair['from'])
    if name.endswith('.write'):
        for i, path in enumerate(paths):
            for other in paths[i+1:]:
                if path[:len(other)] == other or other[:len(path)] == path:
                    raise ValueError('overlapping native write paths')


def equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return set(a) == set(b) and all(equal(a[key], b[key]) for key in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def convert(value, spec):
    if 'values' in spec:
        matches = [pair['to'] for pair in spec['values'] if equal(value, pair['from'])]
        if len(matches) != 1:
            raise ValueError('unmapped native/canonical enum value')
        value = matches[0]
    mode = spec.get('convert', 'identity')
    if mode == 'id_string':
        if type(value) is int:
            value = str(value)
        if not common.opaque_id(value):
            raise ValueError('ID must be an integer or nonempty opaque string')
    elif mode == 'integer':
        if not isinstance(value, str) or not re.fullmatch(r'0|-?[1-9][0-9]*', value):
            raise ValueError('integer conversion must be lossless (no leading zeros)')
        value = int(value)
    return copy.deepcopy(value)


def read_path(record, parts):
    value = record
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and re.fullmatch(r'0|[1-9][0-9]*', part) and int(part) < len(value):
            value = value[int(part)]
        else:
            raise ValueError('missing native field: /' + '/'.join(parts))
    return value


def write_path(record, parts, value):
    node = record
    for i, part in enumerate(parts):
        last = i == len(parts)-1
        default = value if last else ([] if parts[i+1].isdigit() else {})
        if isinstance(node, dict):
            if part not in node:
                node[part] = default
            elif last:
                raise ValueError('duplicate native field')
            node = node[part]
        elif isinstance(node, list) and re.fullmatch(r'0|[1-9][0-9]*', part):
            index = int(part)
            if index > len(node):
                raise ValueError('sparse native array mapping')
            if index == len(node):
                node.append(default)
            elif last:
                raise ValueError('duplicate native array field')
            node = node[index]
        else:
            raise ValueError('conflicting native path containers')


def transform(name, mapping, record):
    validate_mapping(name, mapping)
    if not isinstance(record, dict):
        raise ValueError('record must be an object')
    out = {}
    if name.endswith('.read'):
        for field, spec in mapping.items():
            out[field] = convert(read_path(record, tokens(spec['path'])), spec)
    else:
        if set(record) != set(mapping):
            raise ValueError('write must contain every mapped field and no unreviewed extras')
        # Stable parent/array order even if YAML keys were sorted by a serializer.
        order = lambda item: tuple((0, int(p)) if p.isdigit() else (1, p) for p in tokens(item[1]['path']))
        for field, spec in sorted(mapping.items(), key=order):
            write_path(out, tokens(spec['path']), convert(record[field], spec))
    return out


def validate_catalog(providers):
    systems, mappings = providers.get('systems'), providers.get('records')
    if not isinstance(systems, dict) or set(systems) != {'crm', 'email'}:
        raise ValueError('provider systems must declare crm and email')
    if not isinstance(mappings, dict) or set(mappings) != set(CONTRACTS):
        raise ValueError('provider record catalog differs from contract')
    for name, mapping in mappings.items():
        if mapping is not None:
            validate_mapping(name, mapping)
    for capability, details in providers['capabilities'].items():
        if not details['tool']:
            continue
        system = capability.split('.')[0]
        if system in systems and not common.opaque_id(systems[system]):
            raise ValueError('configured capability needs provider identity: ' + system)
        for record in CAPABILITY_RECORDS.get(capability, []):
            if mappings[record] is None:
                raise ValueError('configured capability needs record mapping: ' + record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--providers', type=Path, default=common.SHARED / 'providers.yaml')
    parser.add_argument('--record', choices=CONTRACTS, required=True)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    try:
        from readback_check import load
        providers = yaml.safe_load(args.providers.read_text())
        validate_catalog(providers)
        out = transform(args.record, providers['records'][args.record], load(args.input))
        print(json.dumps(out, indent=2, allow_nan=False)); return 0
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
        print(json.dumps({'verdict': 'error', 'reason': str(exc)})); return 2


if __name__ == '__main__':
    sys.exit(main())
