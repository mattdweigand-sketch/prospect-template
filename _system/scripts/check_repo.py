#!/usr/bin/env python3
"""Check portable skill pointers and repository hygiene without provider calls."""
import ast
import json
from pathlib import Path
import re
import sys
import yaml
ROOT=Path(__file__).resolve().parents[2]
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
    if re.search(r'CRM[^\n]*\b18[- ]char|--shared[ =]+_shared\b', text, re.I):
        errors.append('stale CRM ID or configuration-directory instruction: '+str(path))
    if LEGACY_RULES.search(text): errors.append('legacy product-specific qualification rule: '+str(path))
    return errors



def procedure_files(root):
    return sorted(p for area in ('setup', 'stages', 'workflows')
                  for p in (Path(root)/area).rglob('procedure.md'))


def section(text, heading):
    match = re.search(r'^## '+re.escape(heading)+r'\s*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    return match.group(1) if match else ''


def table_rows(text):
    return [[cell.strip() for cell in line.strip().strip('|').split('|')]
            for line in text.splitlines() if line.startswith('|')
            and not re.fullmatch(r'[|:\s-]+', line)]


def contract_issues(root, procedure):
    root = Path(root).resolve(); contract = procedure.with_name('CONTEXT.md')
    label = str(contract.relative_to(root)); errors = []
    if not contract.is_file(): return ['missing workflow contract: '+label]
    text = contract.read_text(); detail = procedure.read_text()
    if len(text.splitlines()) > 80: errors.append('contract exceeds 80 lines: '+label)
    headers = {'Inputs': ['Source','File/Location','Section/Scope','Why'],
               'Checkpoints': ['After Step','Agent Presents','Human Decides'],
               'Audit': ['Check','Pass Condition'], 'Outputs': ['Artifact','Location','Format']}
    tables = {}
    for heading, header in headers.items():
        rows = table_rows(section(text, heading)); tables[heading] = rows[1:]
        if not rows or rows[0] != header or len(rows) < 2 or any(len(row) != len(header) or not all(row) for row in rows):
            errors.append('invalid '+heading+' table: '+label)
    numbers = lambda body: re.findall(r'^(\d+)\. ', body, re.M)
    steps = numbers(section(text, 'Process')); detailed = numbers(section(detail, 'Steps'))
    if not steps or steps != [str(i) for i in range(1, len(steps)+1)] or steps != detailed:
        errors.append('process steps do not match procedure: '+label)
    for row in tables['Checkpoints']:
        if row[0] not in steps: errors.append('checkpoint references missing step: '+label)
    if 'Audit' not in detail: errors.append('procedure does not invoke contract Audit: '+label)
    targets = []
    for row in tables['Inputs']:
        if len(row) != 4: continue
        paths = re.findall(r'`([^`]+)`', row[1]); targets.extend(paths)
        if row[0] != 'Working' and not paths: errors.append('input needs an explicit file: '+label)
    if 'procedure.md' not in targets: errors.append('procedure missing from Inputs: '+label)
    targets.extend(re.findall(r'`([^`]+)`', section(text, 'Next')))
    for target in targets:
        resolved = (contract.parent/target).resolve()
        if root not in resolved.parents:
            errors.append('escaping contract path: '+label+': '+target); continue
        # Installed settings do not exist in a fresh template; check their schema owners.
        if resolved.is_relative_to(root/'.local/config'):
            resolved = root/'setup/templates'/resolved.relative_to(root/'.local/config')
        if not resolved.exists(): errors.append('broken contract path: '+label+': '+target)
    return errors


def markdown_issues(path, text):
    errors = []; fence = None
    for line in text.splitlines():
        match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if not match: continue
        marker, rest = match.groups()
        if fence is None: fence = marker
        elif marker[0] == fence[0] and len(marker) >= len(fence) and not rest.strip(): fence = None
    if fence: errors.append('unclosed Markdown fence: '+str(path))
    if (path.name == 'procedure.md' or 'references' in path.parts) and len(text.splitlines()) > 200:
        errors.append('procedure/reference exceeds 200 lines: '+str(path))
    return errors


def layout_issues(root):
    root = Path(root)
    allowed = {'AGENTS.md','CONTEXT.md','README.md','LICENSE','.gitignore',
               'setup','stages','workflows','shared','_system',
               '.agents','.github','.codex','.git','.local','.venv','.pytest_cache','__pycache__'}
    errors = ['unexpected root item: '+p.name for p in root.iterdir() if p.name not in allowed]
    for area in ('setup','stages','workflows','shared','_system'):
        base = root/area
        folders = [base] + [p for p in base.rglob('*') if p.is_dir() and not any(part in ('__pycache__','.pytest_cache') for part in p.parts)]
        for folder in folders:
            # A working contract owns its optional references and output folders.
            if any(parent.name in ('references','output') and (parent.parent/'procedure.md').is_file()
                   for parent in (folder, *folder.parents)):
                continue
            if not (folder/'CONTEXT.md').is_file():
                errors.append('folder needs a purpose contract: '+str(folder.relative_to(root)))
    for folder in list((root/'stages').glob('*')) + list((root/'workflows').glob('*')):
        if folder.is_dir():
            extras = {p.name for p in folder.iterdir()} - {'CONTEXT.md','procedure.md','references','output'}
            if extras: errors.append('implementation or stray files in working folder: '+str(folder.relative_to(root)))
    for procedure in procedure_files(root):
        output = procedure.parent/'output'
        if output.exists() and (not output.is_dir() or any(p.name != '.gitkeep' or not p.is_file() or p.stat().st_size for p in output.iterdir())):
            errors.append('operational output belongs outside the checkout: '+str(output.relative_to(root)))
    return errors


def check(root=ROOT):
    root=Path(root).resolve(); errors=layout_issues(root); workflows=set(); procedures={}
    for procedure in procedure_files(root):
        errors.extend(contract_issues(root, procedure))
        try:
            name=yaml.safe_load(procedure.read_text().split('---\n',2)[1])['workflow']
            if not isinstance(name,str) or not name.strip(): raise ValueError('workflow name required')
            procedures[name]=procedure
            if name in workflows: errors.append('duplicate workflow procedure: '+name)
            workflows.add(name)
        except (IndexError,KeyError,TypeError,ValueError,yaml.YAMLError):
            errors.append('invalid procedure metadata: '+str(procedure.relative_to(root)))
    skills=list((root/'.agents/skills').glob('*/SKILL.md'))
    if {p.parent.name for p in skills} != workflows: errors.append('skills and workflow procedures differ')
    links=0
    for skill in skills:
        source=skill.read_text()
        try:
            front=yaml.safe_load(source.split('---\n',2)[1])
            if front.get('name') != skill.parent.name or not front.get('description'): errors.append('invalid skill metadata: '+skill.parent.name)
        except (IndexError,ValueError,yaml.YAMLError): errors.append('invalid skill frontmatter: '+skill.parent.name)
        destinations=[]
        for target in re.findall(r'\]\(([^)]+)\)',source):
            links+=1; resolved=(skill.parent/target).resolve()
            destinations.append(resolved)
            if root.resolve() not in resolved.parents or not resolved.is_file(): errors.append('broken or escaping skill link: '+target)
        owner=procedures.get(skill.parent.name)
        if owner and (owner.resolve() not in destinations or owner.with_name('CONTEXT.md').resolve() not in destinations):
            errors.append('skill points to the wrong workflow: '+skill.parent.name)
    ignored={'.git','.local','.venv','__pycache__','.pytest_cache'}
    files=[p for p in root.rglob('*') if p.is_file() and not any(part in ignored for part in p.relative_to(root).parts)]
    for path in files:
        if path.suffix=='.py':
            try: ast.parse(path.read_text(),filename=str(path))
            except SyntaxError as exc: errors.append(str(exc))
        if path.suffix in ('.md','.py','.sql','.yaml'):
            errors.extend(neutrality_issues(path.relative_to(root),path.read_text()))
        if path.suffix == '.md': errors.extend(markdown_issues(path.relative_to(root),path.read_text()))
    policy=yaml.safe_load((root/'setup/templates/policy.yaml').read_text())
    if policy['deployment']['mode']!='example': errors.append('starter configuration must stay fictional')
    if any((policy['warehouse']['enabled'],policy['user_scan']['enabled'],policy['arr_growth']['enabled'],policy['prospector']['adoption_source']['enabled'])):
        errors.append('subscription and warehouse starter modules must default off')
    if policy['identity']['timezone']!='UTC' or policy['crm']['house_owner_ids'] or policy['scan']['warm_engagement']['ignored_owner_ids']:
        errors.append('starter identity must not inherit territory-specific time or owner defaults')
    providers=yaml.safe_load((root/'setup/templates/providers.yaml').read_text())
    if any(providers['systems'].values()) or any(providers['records'].values()) or any(any(cap.values()) for cap in providers['capabilities'].values()):
        errors.append('starter providers and mappings must remain unconfigured')
    return {'status':'pass' if not errors else 'fail','workflows':len(workflows),'skills':len(skills),'skill_links':links,'files_checked':len(files),'errors':errors}


if __name__=='__main__':
    result=check(); print(json.dumps(result,indent=2)); sys.exit(bool(result['errors']))
