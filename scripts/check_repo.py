#!/usr/bin/env python3
"""Check portable skill pointers and repository hygiene without provider calls."""
import ast
import json
from pathlib import Path
import re
import sys
import yaml
ROOT=Path(__file__).resolve().parents[1]
# Denylist only: these names are never installed business settings.
SOURCE_MARKERS = re.compile(
    r'perplexity|pplx|AGENTIC_WH|005cv000|analytics\.analytics\.|raw\.salesforce\.'
    r'|stripe_customer_email|product_communications_enabled|dim_subscription_user_daily'
    r'|dim_user_attributes|dim_organizations|int_organization_salesforce_identity'
    r'|dim_organization_subscription_daily|arr_contribution|\bdate_pt\b', re.I)
PROVIDER_ASSUMPTIONS = re.compile(r'salesforce|gmail|sfdc|\bSOQL\b|in:sent|\bWhoId\b|\bWhatId\b|\bOwnerId\b|\bIsClosed\b|\bNumberOfEmployees\b', re.I)
LEGACY_RULES = re.compile(r'employee_use|customer_product|ai_exec_appointment|public_ai_initiative|exec_ai_statements')


def neutrality_issues(path, text):
    # Regression fixtures deliberately contain bad inputs. Check shipped rules,
    # examples, docs and skills; code below defines the denylist itself.
    if 'tests' in path.parts or path.name == 'check_repo.py':
        return []
    errors=[]
    if SOURCE_MARKERS.search(text): errors.append('source-specific brand, identity or warehouse field: '+str(path))
    if PROVIDER_ASSUMPTIONS.search(text): errors.append('hardcoded provider assumption: '+str(path))
    if LEGACY_RULES.search(text): errors.append('legacy product-specific qualification rule: '+str(path))
    return errors



def check(root=ROOT):
    root=Path(root); errors=[]; workflows={p.parent.name for p in (root/'workflows').glob('*/procedure.md')}
    skills=list((root/'.agents/skills').glob('*/SKILL.md'))
    if {p.parent.name for p in skills} != workflows: errors.append('skills and workflow procedures differ')
    links=0
    for skill in skills:
        source=skill.read_text()
        try:
            front=yaml.safe_load(source.split('---\n',2)[1])
            if front.get('name') != skill.parent.name or not front.get('description'): errors.append('invalid skill metadata: '+skill.parent.name)
        except (IndexError,ValueError,yaml.YAMLError): errors.append('invalid skill frontmatter: '+skill.parent.name)
        for target in re.findall(r'\]\(([^)]+)\)',source):
            links+=1; resolved=(skill.parent/target).resolve()
            if root.resolve() not in resolved.parents or not resolved.is_file(): errors.append('broken or escaping skill link: '+target)
    ignored={'.git','.local','.venv','__pycache__','.pytest_cache'}
    files=[p for p in root.rglob('*') if p.is_file() and not any(part in ignored for part in p.relative_to(root).parts)]
    for path in files:
        if path.suffix=='.py':
            try: ast.parse(path.read_text(),filename=str(path))
            except SyntaxError as exc: errors.append(str(exc))
        if path.suffix in ('.md','.py','.sql','.yaml'):
            errors.extend(neutrality_issues(path.relative_to(root),path.read_text()))
    policy=yaml.safe_load((root/'examples/config/policy.yaml').read_text())
    if policy['deployment']['mode']!='example': errors.append('starter configuration must stay fictional')
    if any((policy['warehouse']['enabled'],policy['user_scan']['enabled'],policy['arr_growth']['enabled'],policy['prospector']['adoption_source']['enabled'])):
        errors.append('subscription and warehouse starter modules must default off')
    if policy['identity']['timezone']!='UTC' or policy['crm']['house_owner_ids'] or policy['scan']['warm_engagement']['ignored_owner_ids']:
        errors.append('starter identity must not inherit territory-specific time or owner defaults')
    providers=yaml.safe_load((root/'examples/config/providers.yaml').read_text())
    if any(providers['systems'].values()) or any(providers['records'].values()) or any(any(cap.values()) for cap in providers['capabilities'].values()):
        errors.append('starter providers and mappings must remain unconfigured')
    return {'status':'pass' if not errors else 'fail','workflows':len(workflows),'skills':len(skills),'skill_links':links,'files_checked':len(files),'errors':errors}


if __name__=='__main__':
    result=check(); print(json.dumps(result,indent=2)); sys.exit(bool(result['errors']))
