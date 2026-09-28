"""Missing native evidence must not be represented as an empty successful read."""
import _support
import copy
import unittest
from datetime import timedelta
from test_outreach_gate import PACKET, POL, SHARED, NOW, og

class NativeBoundaries(unittest.TestCase):
    def check(self,p,policy=POL):
        return og.check(p,policy,SHARED,NOW)

    def test_public_source_envelope_is_required(self):
        for key in ('gate','source_url','date_basis'):
            p=copy.deepcopy(PACKET); del p['bundle'][key]
            with self.subTest(key=key): self.assertTrue(self.check(p))

    def test_empty_rows_without_read_receipts_block(self):
        p=copy.deepcopy(PACKET); p['activity']=[]; del p['reads']
        self.assertEqual(len([r for r in self.check(p) if 'completed native-read' in r]),3)

    def test_completed_empty_reads_allow(self):
        p=copy.deepcopy(PACKET); p['activity']=[]
        self.assertEqual(self.check(p),[])

    def test_incomplete_pagination_blocks(self):
        for name in PACKET['reads']:
            p=copy.deepcopy(PACKET); p['reads'][name]['complete']=False
            self.assertTrue(self.check(p))

    def test_stale_future_and_naive_read_times_block(self):
        for stamp in ((NOW-timedelta(hours=25)).isoformat(),(NOW+timedelta(minutes=1)).isoformat(),'2026-09-22T13:00:00'):
            p=copy.deepcopy(PACKET); p['reads']['tasks']['checked_at']=stamp
            self.assertTrue(self.check(p))

    def test_read_scope_cannot_follow_a_changed_recipient(self):
        p=copy.deepcopy(PACKET); p['recipient']['email']='another@acme.example'
        self.assertTrue(any('scope differs' in r for r in self.check(p)))

    def test_short_activity_window_blocks(self):
        p=copy.deepcopy(PACKET); p['reads']['email_sent']['window_start']='2026-09-01'
        self.assertTrue(self.check(p))

    def test_read_call_reference_required(self):
        p=copy.deepcopy(PACKET); p['reads']['tasks']['query_reference']=''
        self.assertTrue(self.check(p))

    def test_unknown_status_is_not_treated_as_open(self):
        p=copy.deepcopy(PACKET); p['activity'][0]['status']='Sent and filed'
        self.assertTrue(any('unmapped Task status' in r for r in self.check(p)))

    def test_configured_completed_status_suppresses(self):
        p=copy.deepcopy(PACKET); p['activity']=[{'kind':'task','date':NOW.date().isoformat(),'who':'003JANE','who_kind':'contact_id','status':'Done','subtype':'Email'}]
        policy=copy.deepcopy(POL); policy['task_status_map']['Done']='completed'
        self.assertTrue(any('suppressed' in r for r in self.check(p,policy)))

    def test_ownership_deal_and_domain_changes_block(self):
        for key,value in (('owner_id','005OTHER'),('owner_is_active',False),('open_deal_ids',['006OPEN']),('domain','another.com')):
            p=copy.deepcopy(PACKET); p['account'][key]=value
            with self.subTest(key=key): self.assertTrue(self.check(p))

    def test_missing_account_is_not_a_valid_handoff(self):
        p=copy.deepcopy(PACKET); del p['account']
        self.assertTrue(self.check(p))
