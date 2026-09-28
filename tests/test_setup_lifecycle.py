"""Disposable setup/refresh rehearsals. No live provider or real business data."""
import _support
import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import yaml
sys.path.insert(0,str(_support.ROOT / 'scripts'))
import setup_common as sc
import setup
import validate_setup as vs
import refresh_sources as refresh
import preflight
import source_snapshot

VOICE = 'Hi Jordan, I saw your supplier review initiative. Our comparison briefs may help your team prepare. Would a sample be useful?'
CLAIM = 'We prepare supplier comparison briefs.'


def git(repo,*args):
    return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgSign=false','-c','user.name=Synthetic Setup','-c','user.email=synthetic@example.test','-C',str(repo),*args],stderr=subprocess.STDOUT).decode().strip()


class SetupLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.source=self.root/'knowledge'; self.source.mkdir()
        (self.source/'offer.txt').write_text(CLAIM+'\nScope is research support, not a purchasing decision.\n')
        (self.source/'voice.txt').write_text(VOICE+'\n')
        git(self.source,'init','-q'); git(self.source,'add','.'); git(self.source,'commit','-qm','Synthetic source')
        self.revision=git(self.source,'rev-parse','HEAD')
        setup.init('initial',self.root)
        self.run=sc.run_path(self.root,'initial'); self.config=self.run/'proposal'
        self.configure()

    def policy(self,fn):
        path=self.config/'policy.yaml'; p=yaml.safe_load(path.read_text()); fn(p)
        path.write_text(yaml.safe_dump(p,sort_keys=False))

    def configure(self):
        def settings(p):
            p['deployment'].update(mode='configured',business_name='Synthetic Advisory',product_name='Supplier Brief Service',review_reference='synthetic meaning review')
            p['identity'].update(owner_email='seller@synthetic-advisory.org',crm_user_id='005123456789012AAA')
            p['email_voice']['source_reference']='voice.txt'
            p['retention']['review_reference']='synthetic retention decision'
        self.policy(settings)
        (self.config/'voice.md').write_text(VOICE+'\n')
        (self.config/'icp.md').write_text('---\nterritory: {min_employees: 200, max_employees: 5000}\nverticals: [{id: professional_services, rank: 1}]\ndisqualifiers: {hard: [automated_purchase_required], recoverable: [unclear_project]}\n---\n# Supplier research ICP\nOrganizations comparing complex suppliers. Target procurement and operations owners.\n')
        (self.config/'signals.md').write_text('---\nadmission: {tier1_min: 1, tier2_min: 2, warehouse_needs_web_tier2: true, warehouse_max_counted: 1}\ntiers:\n  tier1: [{id: supplier_review, freshness_days: 30}]\n  tier2: [{id: procurement_hiring, freshness_days: 30}]\n  tier3: [{id: general_procurement}]\n---\n# Supplier signals\nA current supplier comparison initiative with a named owner qualifies as supplier_review. General procurement mentions do not.\n')
        future=(date.today()+timedelta(days=30)).isoformat()
        (self.config/'talk-track.md').write_text('---\nreview_by: '+future+'\nverify_before_action: true\n---\n# Service messaging\n\n'+CLAIM+'\n\n## Claim boundaries\nResearch support only. The buyer makes the decision.\n')
        sc.write(self.config/'sources.json',{'schema_version':1,'source':str(self.source),'revision':self.revision,'watch_paths':['offer.txt','voice.txt'],'contradictions_path':None,'claims':[{'text':CLAIM,'path':'offer.txt','quote':CLAIM,'kind':'source','attribution':'Synthetic service description','limitations':'No purchasing decision guarantee','public_naming':False}]})
        sc.write(self.run/'previews.json',{
            'clear_fit':{'scenario':'A fictional buyer starts a supplier review','decision':'draft','reason':'The service supports comparison research','draft':VOICE},
            'indirect_fit':{'scenario':'A fictional buyer mentions procurement','decision':'research','reason':'No current project or owner verified','draft':''},
            'poor_fit':{'scenario':'A fictional buyer needs automated purchase approval','decision':'reject','reason':'The service only provides research support','draft':''}})

    def prepare_apply(self):
        setup.prepare('initial',self.root)
        return setup.apply('initial','synthetic approval, not a real user',self.root)

    def test_service_setup_without_providers_or_warehouse(self):
        result=vs.validate(self.config,self.root)
        self.assertEqual(result['claims_checked'],1)
        self.assertEqual(self.prepare_apply()['status'],'applied')
        active=self.root/'.local/config'
        self.assertEqual(sc.hashes(active),sc.read(active/'approval.json')['files'])
        readiness=preflight.check('signal-scan',self.root)
        self.assertEqual(readiness['status'],'missing_provider_mappings')

    def test_service_signal_to_draft_readback_and_proven_followup(self):
        import evidence_gate
        import route_candidate
        import readback_check
        from test_outreach_gate import og
        from test_followup_gate import fg
        from test_scan_verdict import sv
        self.prepare_apply()
        config=self.root/'.local/config'
        policy=yaml.safe_load((config/'policy.yaml').read_text())
        now=datetime.now(timezone.utc); today=now.date()
        page='Acme has launched a supplier comparison project led by Jordan, procurement director.'
        receipt={'account_name':'Acme','account_aliases':['Acme'],'account_domain':'acme.example','source_url':'https://acme.example/news','published_date':today.isoformat(),'quote':page,'evidence_subject':'Acme','signal_type':'supplier_review','quote_speaker':'account','classification':'active_initiative','relevance':'relevant_to_offer','fit_reason':'The project requires the configured comparison-research deliverable.'}
        _,scan,types=evidence_gate.load_rules(config)
        code,evidence=evidence_gate.grade(receipt,page,scan,types,today,now)
        self.assertEqual(code,0)
        self.assertEqual(sv.verdict([evidence])['recommended'],1)
        rules=route_candidate.load_rules(config)
        candidate={'domain':'acme.example','headcount':1000,'signals':[{'signal_type':'supplier_review','tier':'tier1'}],'account_exists':True,'owner_id':policy['identity']['crm_user_id'],'owner_is_active':True,'open_deal_ids':[]}
        routed=route_candidate.check(candidate,rules)
        self.assertEqual(routed['route'],'scan')
        packet={'bundle':evidence['bundle'],'talk_track':{'angle':'Supplier comparison research','persona':'Procurement project owner','pick_reason':'The named owner runs the announced comparison project.'},'recipient':{'email':'jordan@acme.example','name':'Jordan','title':'Procurement director','source':'existing CRM contact with email','contact_id':'003SYNTHETIC'},'activity':[], 'account':{'id':'001SYNTHETIC','domain':'acme.example','owner_id':policy['identity']['crm_user_id'],'owner_is_active':True,'open_deal_ids':[]},'reads':{name:{'complete':True,'query_reference':'synthetic:'+name,'checked_at':now.isoformat(),'account_domain':'acme.example','recipient_email':'jordan@acme.example','window_start':(today-timedelta(days=31)).isoformat()} for name in ('tasks','events','email_sent')},'draft':{'subject':'Supplier comparison project','body':'I saw your supplier comparison project. '+CLAIM+' Would a sample brief be useful?'}}
        self.assertEqual(og.check(packet,policy['outreach'],config,now),[])
        approved={'to':packet['recipient']['email'],**packet['draft']}
        simulated_native={**approved,'cc':[],'bcc':[],'message_id':'synthetic-message','draft_id':'synthetic-draft'}
        self.assertEqual(readback_check.compare(approved,simulated_native,email=True)['verdict'],'match')
        bad={**simulated_native,'bcc':['extra@acme.example']}
        self.assertEqual(readback_check.compare(approved,bad,email=True)['verdict'],'mismatch')
        followup={'sent':[{'message_id':'synthetic-sent','is_sent':True,'thread_id':'synthetic-thread','subject':approved['subject'],'sent_at':now.isoformat(),'to':approved['to']}],'account':{'id':'001SYNTHETIC','owner_id':policy['identity']['crm_user_id']},'contacts':[{'id':'003SYNTHETIC','email':approved['to']}],'tasks':[],'signal':{'signal_type':'supplier_review','angle':'Supplier comparison research'}}
        result=fg.check(followup,'standard',policy,today=today)
        self.assertEqual(result['verdict'],'allow')
        self.assertEqual(result['task']['account_id'],'001SYNTHETIC')
        self.assertEqual(result['task']['contact_id'],'003SYNTHETIC')
        self.assertEqual(readback_check.compare(result['task'],{**result['task'],'Id':'00TSYNTHETIC'})['verdict'],'match')
        followup['sent']=[]
        self.assertEqual(fg.check(followup,'standard',policy,today=today)['verdict'],'block')

    def test_examples_cannot_be_applied(self):
        with self.assertRaisesRegex(ValueError,'fictional examples'):
            vs.validate(_support.SHARED,self.root)

    def test_clear_preview_requires_draft(self):
        p=sc.read(self.run/'previews.json'); p['clear_fit']['draft']=''; sc.write(self.run/'previews.json',p)
        with self.assertRaisesRegex(ValueError,'draft preview'): setup.prepare('initial',self.root)

    def test_source_quote_must_match_pinned_commit(self):
        sources=sc.read(self.config/'sources.json'); sources['claims'][0]['quote']='Unsupported promise'
        sc.write(self.config/'sources.json',sources)
        with self.assertRaisesRegex(ValueError,'quote is absent'): vs.validate(self.config,self.root)

    def test_mutable_worktree_does_not_change_pinned_evidence(self):
        (self.source/'offer.txt').write_text('Uncommitted replacement')
        self.assertEqual(vs.validate(self.config,self.root)['source_revision'],self.revision)

    def test_short_or_branch_source_revision_rejected(self):
        for ref in ('HEAD',self.revision[:8]):
            sources=sc.read(self.config/'sources.json'); sources['revision']=ref; sc.write(self.config/'sources.json',sources)
            with self.assertRaisesRegex(ValueError,'full commit hash'): vs.validate(self.config,self.root)

    def test_voice_must_be_in_pinned_source(self):
        (self.config/'voice.md').write_text(VOICE+' This additional sentence was not approved.')
        with self.assertRaisesRegex(ValueError,'voice sample'): vs.validate(self.config,self.root)

    def test_proposal_edit_invalidates_review(self):
        setup.prepare('initial',self.root)
        (self.config/'icp.md').write_text((self.config/'icp.md').read_text()+'\nA new rule.\n')
        with self.assertRaisesRegex(ValueError,'proposal changed'): setup.apply('initial','synthetic',self.root)
        self.assertFalse((self.root/'.local/config').exists())

    def test_review_and_preview_edits_invalidate_approval(self):
        for file in ('review.md','previews.json'):
            setup.prepare('initial',self.root)
            p=self.run/file; original=p.read_bytes(); p.write_bytes(original+b'\n')
            with self.subTest(file=file), self.assertRaisesRegex(ValueError,'changed'):
                setup.apply('initial','synthetic',self.root)
            p.write_bytes(original)

    def test_changed_active_preimage_blocks(self):
        self.prepare_apply(); setup.init('update',self.root)
        update=sc.run_path(self.root,'update')
        shutil.copyfile(self.config/'policy.yaml',update/'proposal/policy.yaml')
        shutil.copyfile(self.run/'previews.json',update/'previews.json')
        setup.prepare('update',self.root)
        (self.root/'.local/config/voice.md').write_text('Concurrent edit')
        with self.assertRaisesRegex(ValueError,'active configuration changed'): setup.apply('update','synthetic',self.root)

    def test_active_edit_breaks_preflight(self):
        self.prepare_apply()
        path=self.root/'.local/config/icp.md'; path.write_text(path.read_text()+'\nChanged rule\n')
        with self.assertRaisesRegex(ValueError,'changed after approval'): preflight.check('signal-scan',self.root)

    def test_missing_approval_and_double_application_block(self):
        setup.prepare('initial',self.root)
        with self.assertRaisesRegex(ValueError,'approval reference'): setup.apply('initial','',self.root)
        setup.apply('initial','synthetic',self.root)
        with self.assertRaisesRegex(ValueError,'already applied'): setup.apply('initial','synthetic',self.root)

    def test_concurrent_apply_lock_blocks_without_writes(self):
        setup.prepare('initial',self.root); (self.root/'.local/apply.lock').write_text('another run')
        with self.assertRaises(FileExistsError): setup.apply('initial','synthetic',self.root)
        self.assertFalse((self.root/'.local/config').exists())

    def test_custom_native_status_map(self):
        def change(p):
            p['outreach']['task_status_map']={'Done':'completed','Planned':'open','Cancelled':'cancelled'}
            p['followup']['task']['status']='Planned'; p['followup']['closed_statuses']=['Done','Cancelled']
        self.policy(change)
        self.assertEqual(vs.validate(self.config,self.root)['status'],'valid_configuration_not_approval')

    def test_optional_module_requires_reviewed_query(self):
        self.policy(lambda p:p['user_scan'].update(enabled=True))
        with self.assertRaisesRegex(ValueError,'enabled warehouse'): vs.validate(self.config,self.root)
        self.policy(lambda p:p['warehouse'].update(enabled=True,name='SYNTHETIC_WH'))
        with self.assertRaisesRegex(ValueError,'private copy'): vs.validate(self.config,self.root)

    def test_provider_mapping_is_not_live_access(self):
        providers=yaml.safe_load((self.config/'providers.yaml').read_text())
        import provider_map
        providers['systems']={'crm':'Synthetic CRM','email':'Synthetic Mail'}
        providers['records']={name:{field:{'path':'/'+field} for field in fields} for name,fields in provider_map.CONTRACTS.items()}
        for capability in providers['capabilities'].values():
            capability.update(tool='synthetic_tool',input_mapping='synthetic fields',output_mapping='synthetic fields',completion='all pages complete',verification_reference='synthetic schema')
        (self.config/'providers.yaml').write_text(yaml.safe_dump(providers))
        self.prepare_apply()
        self.assertEqual(preflight.check('signal-scan',self.root)['status'],'configured_needs_live_reads')
        with self.assertRaisesRegex(ValueError,'disabled'): preflight.check('signal-user-scan',self.root)

    def test_run_traversal_and_symlinks_rejected(self):
        with self.assertRaises(ValueError): setup.init('../escape',self.root)
        outside=self.root/'outside'; outside.mkdir()
        (self.root/'.local/setup/link').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'): setup.init('link',self.root)
        (self.config/'voice.md').unlink(); (self.config/'voice.md').symlink_to(self.source/'voice.txt')
        with self.assertRaisesRegex(ValueError,'symlink'): vs.validate(self.config,self.root)

    def test_refresh_compares_pinned_baseline_and_stages_only(self):
        self.prepare_apply()
        original=sc.hashes(self.root/'.local/config')
        (self.source/'offer.txt').write_text('The original offer is withdrawn.\n')
        git(self.source,'add','.'); git(self.source,'commit','-qm','Synthetic retirement')
        revision=git(self.source,'rev-parse','HEAD')
        report=refresh.stage(revision,'refresh',self.root)
        self.assertEqual(report['baseline'],self.revision)
        self.assertEqual(report['changed'],[{'path':'offer.txt','status':'changed'}])
        self.assertEqual(sc.hashes(self.root/'.local/config'),original)
        proposal=sc.run_path(self.root,'refresh')/'proposal'
        with self.assertRaisesRegex(ValueError,'review_reference'): vs.validate(proposal,self.root)
        p=yaml.safe_load((proposal/'policy.yaml').read_text()); p['deployment']['review_reference']='synthetic refreshed review'; (proposal/'policy.yaml').write_text(yaml.safe_dump(p))
        with self.assertRaisesRegex(ValueError,'quote is absent'): vs.validate(proposal,self.root)

    def test_refresh_reports_deleted_watched_file(self):
        self.prepare_apply(); (self.source/'offer.txt').unlink()
        git(self.source,'add','-A'); git(self.source,'commit','-qm','Synthetic deletion')
        report=refresh.inspect(git(self.source,'rev-parse','HEAD'),self.root)
        self.assertEqual(report['changed'][0]['status'],'missing_or_nonregular')

    def test_update_preserves_unrelated_configuration_and_keeps_backup(self):
        self.prepare_apply(); setup.init('update',self.root)
        update=sc.run_path(self.root,'update'); path=update/'proposal/policy.yaml'
        p=yaml.safe_load(path.read_text()); self.assertIsNone(p['deployment']['review_reference'])
        p['deployment']['review_reference']='synthetic update'; p['outreach']['lint']['max_body_words']=110
        path.write_text(yaml.safe_dump(p)); shutil.copyfile(self.run/'previews.json',update/'previews.json')
        before=(self.root/'.local/config/icp.md').read_bytes()
        setup.prepare('update',self.root); setup.apply('update','synthetic update approval',self.root)
        self.assertEqual((self.root/'.local/config/icp.md').read_bytes(),before)
        self.assertTrue((update/'previous-config/approval.json').is_file())

    def test_source_pin_ignores_local_git_replacement_refs(self):
        (self.source/'offer.txt').write_text('A substituted source with a different assertion.\n')
        git(self.source,'add','.'); git(self.source,'commit','-qm','Synthetic replacement target')
        replacement=git(self.source,'rev-parse','HEAD')
        git(self.source,'replace',self.revision,replacement)
        self.assertEqual(vs.validate(self.config,self.root)['source_revision'],self.revision)

    def test_failed_install_restores_previous_configuration(self):
        self.prepare_apply(); setup.init('update',self.root)
        update=sc.run_path(self.root,'update')
        shutil.copyfile(self.config/'policy.yaml',update/'proposal/policy.yaml')
        shutil.copyfile(self.run/'previews.json',update/'previews.json')
        setup.prepare('update',self.root)
        active=self.root/'.local/config'; original=sc.hashes(active)
        rename=Path.rename
        def fail_stage(path,target):
            if path.name=='config' and path.parent.name.startswith('.config-stage-'):
                raise OSError('synthetic interrupted install')
            return rename(path,target)
        with mock.patch.object(Path,'rename',fail_stage):
            with self.assertRaisesRegex(OSError,'interrupted install'):
                setup.apply('update','synthetic',self.root)
        self.assertEqual(sc.hashes(active),original)
        self.assertFalse((self.root/'.local/apply.lock').exists())
        self.assertFalse((update/'applied.json').exists())

    def test_source_symlink_cannot_supply_evidence(self):
        (self.source/'alias.txt').symlink_to('offer.txt'); git(self.source,'add','.'); git(self.source,'commit','-qm','Synthetic alias')
        source=sc.read(self.config/'sources.json'); source['revision']=git(self.source,'rev-parse','HEAD'); source['watch_paths'].append('alias.txt')
        sc.write(self.config/'sources.json',source)
        with self.assertRaisesRegex(ValueError,'not a regular committed file'): vs.validate(self.config,self.root)


class SourceSnapshot(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve(); self.input=self.root/'input'; self.input.mkdir()
        (self.input/'original.bin').write_bytes(b'original\x00bytes\xff')
        (self.input/'extract.txt').write_text('Synthetic extracted content')
        self.manifest=self.input/'manifest.json'
        sc.write(self.manifest,{'sources':[{'path':'original.bin','reference':'materials/original.bin','origin':'Synthetic supplied file','kind':'source'}, {'path':'extract.txt','reference':'materials/extract.txt','origin':'Synthetic extraction','kind':'extracted_text','derived_from':'materials/original.bin'}]})

    def test_original_bytes_and_history_are_preserved(self):
        first=self.root/'.local/sources/first'; second=self.root/'.local/sources/second'
        result=source_snapshot.snapshot(self.manifest,first,root=self.root)
        self.assertEqual((first/'materials/original.bin').read_bytes(),b'original\x00bytes\xff')
        (self.input/'extract.txt').write_text('Updated synthetic extraction')
        updated=source_snapshot.snapshot(self.manifest,second,first,self.root)
        self.assertNotEqual(result['revision'],updated['revision'])
        self.assertEqual(git(second,'rev-parse','HEAD^'),result['revision'])
        self.assertEqual(git(first,'rev-parse','HEAD'),result['revision'])
        self.assertEqual(git(second,'remote'), '')

    def test_snapshot_outside_ignored_directory_rejected(self):
        with self.assertRaises(ValueError): source_snapshot.snapshot(self.manifest,self.root/'public',root=self.root)

    def test_symlinked_destination_parent_rejected(self):
        outside=self.root/'outside'; outside.mkdir(); (self.root/'.local').mkdir(); (self.root/'.local/sources').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'): source_snapshot.snapshot(self.manifest,self.root/'.local/sources/escape',root=self.root)

    def test_changed_original_requires_fresh_extraction(self):
        first=self.root/'.local/sources/first'; source_snapshot.snapshot(self.manifest,first,root=self.root)
        manifest=sc.read(self.manifest); manifest['sources']=manifest['sources'][:1]; sc.write(self.manifest,manifest)
        (self.input/'original.bin').write_bytes(b'new original')
        with self.assertRaisesRegex(ValueError,'replace the extraction'): source_snapshot.snapshot(self.manifest,self.root/'.local/sources/second',first,self.root)

    def test_casefold_and_file_directory_collisions_rejected(self):
        for ref in ('MATERIALS/ORIGINAL.BIN','materials/original.bin/child'):
            manifest=sc.read(self.manifest); manifest['sources'][1]['reference']=ref; manifest['sources'][1]['kind']='source'; sc.write(self.manifest,manifest)
            with self.assertRaisesRegex(ValueError,'collide|conflict'): source_snapshot.snapshot(self.manifest,self.root/'.local/sources/collision',root=self.root)
