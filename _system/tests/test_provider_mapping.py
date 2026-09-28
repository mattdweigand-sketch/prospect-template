"""Synthetic adapter contracts; no production API compatibility or provider calls."""
import _support
import copy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'_system/scripts'))
sys.path.insert(0, str(ROOT/'_system/scripts'))
import common
import provider_map as pm
import readback_check as rb
import followup_gate as fg
from test_outreach_gate import pk, POLICY as OPOL, NOW, og


def mapping(name, prefix=''):
    return {key: {'path': prefix+'/'+key} for key in pm.CONTRACTS[name]}


def catalog():
    value=yaml.safe_load((ROOT/'setup/templates/providers.yaml').read_text())
    value['systems']={'crm':'Synthetic CRM','email':'Synthetic Mail'}
    value['records']={name:mapping(name) for name in pm.CONTRACTS}
    return value


class ProviderContracts(unittest.TestCase):
    def test_two_provider_shapes_send_proof_task_and_draft_readback(self):
        for nested in (False,True):
            with self.subTest(nested=nested):
                policy=common.load_policy()
                policy['identity']['crm_user_id']='42' if nested else 'owner:CaseA'
                prefix='/properties' if nested else ''
                draft={'to':'jane@acme.example','subject':'Project question','body':'Hello.\nA question.','cc':[],'bcc':[]}
                write=mapping('email.draft.write',prefix)
                native=pm.transform('email.draft.write',write,draft)
                container=native['properties'] if nested else native
                container['id']='draft:1'
                actual=pm.transform('email.draft.read',mapping('email.draft.read',prefix),native)
                self.assertEqual(rb.compare(draft,actual,email=True)['verdict'],'match')
                container['bcc']=['unexpected@acme.example']
                self.assertEqual(rb.compare(draft,pm.transform('email.draft.read',mapping('email.draft.read',prefix),native),email=True)['verdict'],'mismatch')
                container['bcc']=[]
                container.update(message_id='sent:1',sent_at='2026-09-21T14:05:00-07:00',is_sent='delivered' if nested else True)
                read=mapping('email.message.read',prefix)
                if nested: read['is_sent']['values']=[{'from':'delivered','to':True},{'from':'draft','to':False}]
                message=pm.transform('email.message.read',read,native)
                self.assertNotIn('thread_id',message)
                packet={'sent':[message],'account':{'id':'123' if nested else 'account:CaseA','owner_id':policy['identity']['crm_user_id']},'contacts':[{'id':'987' if nested else 'contact:CaseB','email':draft['to']}],'tasks':[],'signal':{'signal_type':'announced_initiative','angle':'Reviewed project support'}}
                result=fg.check(packet,'standard',policy,today=date(2026,9,21))
                self.assertEqual(result['verdict'],'allow',result)
                task=result['task']
                tw=mapping('crm.task.write',prefix); tr=mapping('crm.task.read',prefix)
                if nested:
                    for key in ('owner_id','account_id','contact_id'):
                        tw[key]['convert']='integer'; tr[key]['convert']='id_string'
                    tw['status']['values']=[{'from':'Not Started','to':'waiting'}]
                    tr['status']['values']=[{'from':'waiting','to':'Not Started'}]
                native_task=pm.transform('crm.task.write',tw,task)
                body=native_task['properties'] if nested else native_task
                if nested:
                    self.assertIs(type(body['account_id']),int)
                    self.assertEqual(body['status'],'waiting')
                body['id']='task:1'
                returned=pm.transform('crm.task.read',tr,native_task)
                self.assertEqual(rb.compare(task,returned)['verdict'],'match')
                body['contact_id']=986 if nested else 'contact:Wrong'
                self.assertEqual(rb.compare(task,pm.transform('crm.task.read',tr,native_task))['verdict'],'mismatch')
                message['is_sent']=False
                self.assertIn('native sent state is not confirmed',fg.check(packet,'standard',policy,today=date(2026,9,21))['reasons'])

    def test_missing_native_field_cannot_be_invented(self):
        with self.assertRaisesRegex(ValueError,'missing native field'):
            pm.transform('email.draft.read',mapping('email.draft.read'),{'id':'d','to':'x','subject':'s','body':'b','cc':[]})

    def test_incomplete_or_unknown_record_shape(self):
        for name, fields in [('crm.task.write',{}),('unknown',{})]:
            with self.assertRaises(ValueError): pm.validate_mapping(name,fields)

    def test_write_refuses_extra_and_missing_approved_fields(self):
        for record in ({'owner_id':'123','unreviewed':True},{}):
            with self.assertRaisesRegex(ValueError,'every mapped field'):
                pm.transform('crm.owner.write',mapping('crm.owner.write'),record)

    def test_overlapping_paths_and_conflicting_containers_fail(self):
        for second in ('/same','/same/nested'):
            m=mapping('crm.account.write');m['name']['path']='/same';m['website']['path']=second
            with self.assertRaisesRegex(ValueError,'overlapping'):pm.validate_mapping('crm.account.write',m)
        with self.assertRaisesRegex(ValueError,'sparse'):
            pm.transform('crm.owner.write',{'owner_id':{'path':'/owners/2/id'}},{'owner_id':'123'})

    def test_nested_arrays_and_escaped_pointer_keys(self):
        m={'owner_id':{'path':'/owners/0/user~1id~0'}}
        actual=pm.transform('crm.owner.write',m,{'owner_id':'OWNER:A'})
        self.assertEqual(actual,{'owners':[{'user/id~':'OWNER:A'}]})
        self.assertEqual(pm.read_path(actual,pm.tokens(m['owner_id']['path'])),'OWNER:A')

    def test_numeric_conversion_is_explicit_and_lossless(self):
        for bad in ('001','+1','1.0',' 1',True,1):
            with self.assertRaises(ValueError): pm.convert(bad,{'convert':'integer'})
        for bad in (True,1.0,None,'',' bad '):
            with self.assertRaises(ValueError): pm.convert(bad,{'convert':'id_string'})
        self.assertEqual(pm.convert(123,{'convert':'id_string'}),'123')
        self.assertEqual(pm.convert('Case:A',{'convert':'id_string'}),'Case:A')

    def test_enum_unknown_duplicate_and_bool_number_ambiguity(self):
        spec={'values':[{'from':True,'to':'sent'}]}
        with self.assertRaises(ValueError):pm.convert(1,spec)
        with self.assertRaises(ValueError):pm.convert([1],{'values':[{'from':[True],'to':'sent'}]})
        with self.assertRaises(ValueError):pm.convert('draft',spec)
        m={'owner_id':{'path':'/owner','values':[{'from':'a','to':'x'},{'from':'a','to':'y'}]}}
        with self.assertRaisesRegex(ValueError,'duplicate'):pm.validate_mapping('crm.owner.write',m)

    def test_capability_requires_system_and_corresponding_mappings(self):
        c=catalog();c['capabilities']['crm.create_task']['tool']='synthetic.create'
        c['systems']['crm']=None
        with self.assertRaisesRegex(ValueError,'identity'):pm.validate_catalog(c)
        c['systems']['crm']='Synthetic CRM';c['records']['crm.task.read']=None
        with self.assertRaisesRegex(ValueError,'record mapping'):pm.validate_catalog(c)

    def test_email_readback_requires_both_recipient_fields(self):
        proposal={'to':'jane@acme.example','subject':'s','body':'b'}
        for actual in (proposal,{**proposal,'cc':[]},{**proposal,'bcc':[]}):
            self.assertEqual(rb.compare(proposal,actual,email=True)['verdict'],'mismatch')

    def test_cli_outputs_mapping_and_failure_without_provider_calls(self):
        with tempfile.TemporaryDirectory() as td:
            providers=Path(td)/'providers.yaml';providers.write_text(yaml.safe_dump(catalog()))
            packet=Path(td)/'input.json';packet.write_text('{"owner_id":"user-123"}')
            command=[sys.executable,str(ROOT/'_system/scripts/provider_map.py'),'--providers',str(providers),'--record','crm.owner.write','--input',str(packet)]
            out=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(out.returncode,0,out.stdout+out.stderr)
            self.assertEqual(json.loads(out.stdout),{'owner_id':'user-123'})
            packet.write_text('{}');out=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(out.returncode,2,out.stdout)
            self.assertEqual(json.loads(out.stdout)['verdict'],'error')

    def test_opaque_contact_ids_compare_exactly_and_unknown_recipient_suppresses(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        p=pk();p['recipient']['contact_id']='person:CaseA'
        p['activity']=[{'kind':'event','date':'2026-09-22','who':'person:CaseA','who_kind':'contact_id'}]
        check=lambda:og.check(p,OPOL['outreach'],_support.SHARED,NOW)
        self.assertTrue(any(x.startswith('suppressed') for x in check()))
        p['activity'][0]['who']='person:casea'
        self.assertFalse(any(x.startswith('suppressed') for x in check()))
        p['recipient']['contact_id']=None;p['recipient']['source']='User supplied in this conversation'
        self.assertTrue(any(x.startswith('suppressed') for x in check()))


if __name__=='__main__':unittest.main()
