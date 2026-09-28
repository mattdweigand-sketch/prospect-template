"""Render the small fixed policy templates with explicit, shared field contracts."""
import re
from string import Formatter


def render(template, **values):
    if not isinstance(template, str) or not template.strip():
        raise ValueError('template must be a nonblank string')
    for _, field, spec, conversion in Formatter().parse(template):
        if field is not None and (field not in values or spec or conversion):
            raise ValueError('unsupported template placeholder: ' + str(field))
    return template.format(**values)


def followup_description(template, message_id, thread_id, signal_type, angle):
    # unit is retained for existing configurations; both names describe the historical angle.
    return render(template, message_id=message_id, thread_id=thread_id,
                  signal_type=signal_type, angle=angle, unit=angle)


def forbidden(policy):
    try:
        return re.compile(policy['draft_forbidden_pattern'], re.I)
    except re.error as exc:
        raise ValueError('invalid arr_growth.draft_forbidden_pattern: ' + str(exc)) from exc


def build_draft(row, policy, forbid):
    draft = policy['draft']
    first = row['contacts'][0].get('first_name') if row['contacts'] else None
    if isinstance(first, str) and first.strip().lower() == 'null':
        first = None
    greeting = render(draft['greeting_person'], first_name=first.strip()) if first and first.strip() \
        else render(draft['greeting_team'], account_name=row['account']['name'])
    subject = render(draft['subject'])
    body = render(draft['body']).rstrip('\n')
    hit = forbid.search(subject) or forbid.search(body)
    if hit:
        raise ValueError(f'draft template contains a forbidden token {hit.group(0)!r}. Fix arr_growth.draft in policy.yaml')
    return {'to': row['billing_email'], 'subject': subject, 'body': f'{greeting}\n\n{body}'}


def module_previews(policy, workflow=None):
    """Generate exact optional-module wording for the hash-bound setup review."""
    previews = {}
    if policy['user_scan']['enabled'] and workflow in (None, 'signal-user-scan'):
        previews['user_scan'] = dict(policy['user_scan']['statements'])
    if policy['arr_growth']['enabled'] and workflow in (None, 'signal-arr-growth'):
        pol = policy['arr_growth']
        row = {'billing_email': 'jordan@buyer.example', 'account': {'name': 'Synthetic Buyer'},
               'contacts': [{'first_name': 'Jordan'}]}
        previews['arr_growth_person'] = build_draft(row, pol, forbidden(pol))
        row['contacts'] = []
        previews['arr_growth_team'] = build_draft(row, pol, forbidden(pol))
    return previews
