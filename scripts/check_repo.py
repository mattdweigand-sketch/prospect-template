#!/usr/bin/env python3
"""Check portable skill pointers and repository hygiene without provider calls."""
import ast
import json
from pathlib import Path
import re
import sys
import yaml
ROOT=Path(__file__).resolve().parents[1]


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
        if path.suffix in ('.md','.py','.sql','.yaml') and path.name not in ('BUILD-REPORT.md','check_repo.py'):
            text=path.read_text()
            if re.search(r'005cv000|matt\.weigand@|analytics\.analytics\.|raw\.salesforce\.',text): errors.append('source-specific identity/schema: '+str(path.relative_to(root)))
    return {'status':'pass' if not errors else 'fail','workflows':len(workflows),'skills':len(skills),'skill_links':links,'files_checked':len(files),'errors':errors}


if __name__=='__main__':
    result=check(); print(json.dumps(result,indent=2)); sys.exit(bool(result['errors']))
