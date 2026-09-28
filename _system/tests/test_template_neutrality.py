"""Verify business-independent fit and guard against source-specific defaults."""
import _support
import copy
from datetime import date, datetime, timezone
from pathlib import Path
import sys
import shutil
import tempfile
import unittest
import yaml
sys.path.insert(0,str(_support.ROOT/'_system/scripts'))
import check_repo
import common
import evidence_gate
from test_evidence_gate import receipt
from test_outreach_gate import PACKET, POL, SHARED, NOW, og
from test_scan_verdict import sv

class TemplateNeutrality(unittest.TestCase):
    def test_starter_is_unconfigured_and_modules_are_optional(self):
        p=yaml.safe_load((_support.EXAMPLES/'policy.yaml').read_text())
        self.assertEqual(p['deployment']['mode'],'example')
        self.assertEqual(p['identity']['timezone'],'UTC')
        self.assertEqual(p['crm']['house_owner_ids'],[])
        self.assertEqual(p['scan']['warm_engagement']['ignored_owner_ids'],[])
        self.assertFalse(p['warehouse']['enabled'])
        self.assertFalse(p['user_scan']['enabled'])
        self.assertFalse(p['arr_growth']['enabled'])
        self.assertFalse(p['prospector']['adoption_source']['enabled'])

    def test_a_customer_facing_manufacturing_initiative_can_qualify(self):
        page='Acme is launching a new customer product line and selecting component suppliers.'
        r=receipt(signal_type='announced_initiative',published_date='2026-09-21',quote=page,
                  fit_reason='The configured component offer fits the published supplier requirements.')
        _,scan,types=evidence_gate.load_rules(SHARED)
        code,out=evidence_gate.grade(r,page,scan,types,date(2026,9,21),datetime(2026,9,21,12,tzinfo=timezone.utc))
        self.assertEqual(code,0)
        self.assertEqual(sv.verdict([out])['recommended'],1)
        p=copy.deepcopy(PACKET); p['bundle']=out['bundle']
        p['bundle']['checked_at']=NOW.isoformat()
        p['talk_track']={'angle':'Component qualification','persona':'Product sourcing owner','pick_reason':'The owner is selecting components for the announced product.'}
        p['draft']={'subject':'Component selection','body':'I saw your new product line and supplier selection. Would a component sample be useful?'}
        self.assertEqual(og.check(p,POL,SHARED,NOW),[])

    def test_facilities_service_with_custom_signal_can_qualify(self):
        page='Acme is opening a distribution center and evaluating building-maintenance contractors.'
        types={'facility_opening':{'tier':'tier1','freshness_days':30,'source':None}}
        r=receipt(signal_type='facility_opening',published_date='2026-09-21',quote=page,
                  fit_reason='The configured facilities service covers the stated maintenance work.')
        code,out=evidence_gate.grade(r,page,common.load_policy(SHARED)['scan'],types,date(2026,9,21))
        self.assertEqual(code,0)
        self.assertEqual(out['bundle']['signal_type'],'facility_opening')

    def test_fit_reason_is_required_through_handoff(self):
        from test_evidence_gate import PAGE
        _,scan,types=evidence_gate.load_rules(SHARED)
        for reason in (None,'','   '):
            code,_=evidence_gate.grade(receipt(fit_reason=reason),PAGE,scan,types,date(2026,9,21))
            self.assertEqual(code,2)
            p=copy.deepcopy(PACKET); p['bundle']['fit_reason']=reason
            self.assertTrue(any('fit_reason' in x for x in og.check(p,POL,SHARED,NOW)))
            self.assertEqual(sv.verdict([{'outcome':'qualified','bundle':p['bundle']}])['reason'],'qualified_bundle_without_fit_reason')

    def test_legacy_relevance_is_not_silently_reinterpreted(self):
        from test_evidence_gate import PAGE
        _,scan,types=evidence_gate.load_rules(SHARED)
        for legacy in ('employee_use','customer_product'):
            code,_=evidence_gate.grade(receipt(relevance=legacy),PAGE,scan,types,date(2026,9,21))
            self.assertEqual(code,2)

    def test_hygiene_detects_vendor_schema_and_legacy_gate_regressions(self):
        for payload in ('Perplexity','stripe_customer_email','analytics.analytics.table','relevance = employee_use','salesforce.query','gmail.search','SOQL','WhoId','CRM Account Id (18 char)','--shared _shared'):
            with self.subTest(payload=payload):
                self.assertTrue(check_repo.neutrality_issues(Path('setup/templates/signals.md'),payload))
        self.assertEqual(check_repo.neutrality_issues(Path('shared/providers.md'),'Use configured warehouse tools.'),[])


class LayoutRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'template'
        shutil.copytree(_support.ROOT, self.root,
                        ignore=shutil.ignore_patterns('.git','.local','.venv','__pycache__','.pytest_cache'))

    def test_stray_root_file_is_rejected(self):
        (self.root/'notes.txt').write_text('unfiled scratch note')
        self.assertIn('unexpected root item: notes.txt', check_repo.check(self.root)['errors'])

    def test_code_in_working_stage_is_rejected(self):
        (self.root/'stages/02-research/helper.py').write_text('pass\n')
        self.assertTrue(any('stray files in working folder' in e for e in check_repo.check(self.root)['errors']))

    def test_folder_without_purpose_contract_is_rejected(self):
        (self.root/'_system/queries/CONTEXT.md').unlink()
        self.assertIn('folder needs a purpose contract: _system/queries', check_repo.check(self.root)['errors'])

    def test_skill_must_target_its_own_workflow(self):
        path=self.root/'.agents/skills/signal-scan/SKILL.md'
        path.write_text(path.read_text().replace('stages/02-research/', 'stages/03-outreach/'))
        self.assertIn('skill points to the wrong workflow: signal-scan', check_repo.check(self.root)['errors'])

    def test_optional_references_and_empty_output_are_supported(self):
        stage=self.root/'stages/02-research'
        (stage/'references').mkdir(); (stage/'references/guide.md').write_text('# Search examples\n')
        (stage/'output').mkdir(); (stage/'output/.gitkeep').touch()
        self.assertEqual(check_repo.check(self.root)['errors'], [])

    def test_customer_output_is_not_allowed_in_checkout(self):
        output=self.root/'stages/02-research/output'; output.mkdir()
        (output/'account.json').write_text('{"account":"private"}')
        self.assertTrue(any('operational output belongs outside' in e for e in check_repo.check(self.root)['errors']))

    def test_procedure_must_be_a_real_explicit_input(self):
        path=self.root/'stages/02-research/CONTEXT.md'; original=path.read_text()
        for target in ('missing.md', '../../../outside.md'):
            with self.subTest(target=target):
                path.write_text(original.replace('`procedure.md` | Full file', '`'+target+'` | Full file'))
                errors=check_repo.check(self.root)['errors']
                self.assertTrue(any('procedure missing from Inputs' in e for e in errors))
                self.assertTrue(any('contract path' in e for e in errors))

    def test_input_scope_and_output_format_are_required(self):
        path=self.root/'stages/02-research/CONTEXT.md'; original=path.read_text()
        for before, after, error in (('| Full file |','| |','invalid Inputs'),
                                      ('| Artifact | Location | Format |','| Artifact | Location |','invalid Outputs')):
            with self.subTest(error=error):
                path.write_text(original.replace(before,after))
                self.assertTrue(any(error in e for e in check_repo.check(self.root)['errors']))

    def test_checkpoint_must_reference_a_process_step(self):
        path=self.root/'stages/03-outreach/CONTEXT.md'
        path.write_text(path.read_text().replace('| 8 |','| 99 |'))
        self.assertTrue(any('checkpoint references missing step' in e for e in check_repo.check(self.root)['errors']))

    def test_process_numbering_must_match_procedure(self):
        path=self.root/'stages/03-outreach/CONTEXT.md'
        path.write_text(path.read_text().replace('9. After exact approval','11. After exact approval'))
        self.assertTrue(any('process steps do not match procedure' in e for e in check_repo.check(self.root)['errors']))

    def test_procedure_must_invoke_the_audit(self):
        path=self.root/'workflows/adoption/procedure.md'
        path.write_text(path.read_text().replace('Audit','review'))
        self.assertTrue(any('does not invoke contract Audit' in e for e in check_repo.check(self.root)['errors']))

    def test_contract_and_reference_line_budgets(self):
        for rel, limit, error in (('stages/02-research/CONTEXT.md',80,'contract exceeds'),
                                  ('stages/02-research/procedure.md',200,'procedure/reference exceeds'),
                                  ('setup/references/installation.md',200,'procedure/reference exceeds')):
            with self.subTest(path=rel):
                path=self.root/rel; original=path.read_text()
                path.write_text(original+'\n'*(limit+1-len(original.splitlines())))
                self.assertTrue(any(error in e for e in check_repo.check(self.root)['errors']))
                path.write_text(original)

    def test_nested_report_fences_must_balance(self):
        path=self.root/'workflows/adoption/procedure.md'
        path.write_text(path.read_text().replace('````text','```').replace('````','```'))
        self.assertTrue(any('unclosed Markdown fence' in e for e in check_repo.check(self.root)['errors']))
