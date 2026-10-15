import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ledgerguard.engine import reconcile,parse_csv,money,near
from ledgerguard import store
ROOT=Path(__file__).resolve().parent.parent
SAMPLES={k:(ROOT/'samples'/f'{k}.csv').read_text() for k in ['invoices','payments','statements']}
class EngineTests(unittest.TestCase):
    def test_known_findings(self):
        result=reconcile(SAMPLES)
        self.assertEqual(result['counts'],dict(invoices=5,payments=4,statements=3))
        self.assertEqual({c['kind']:c['amount_minor'] for c in result['cases']},{'possible_duplicate':120000,'overpayment':20000,'unmatched_payment':95000,'missing_invoice':42500,'statement_difference':5000})
        self.assertFalse(any('INV-5' in c['records'] for c in result['cases']))
    def test_currency_isolation(self):
        data=dict(SAMPLES);data['payments']=data['payments'].replace('GBP','EUR')
        result=reconcile(data)
        self.assertFalse(any(c['kind']=='overpayment' for c in result['cases']))
    def test_no_pair_explosion(self):
        data=dict(SAMPLES);data['invoices']+='INV-6,Northstar Supplies,NS-1001,1200.00,GBP,2026-09-02\n'
        duplicates=[c for c in reconcile(data)['cases'] if c['kind']=='possible_duplicate']
        self.assertEqual(len(duplicates),1);self.assertEqual(duplicates[0]['amount_minor'],240000)
    def test_money_rejects_invalid(self):
        for value in ['NaN','Infinity','-1','0','0.001','1e3','1000000001']:
            with self.subTest(value=value),self.assertRaises(ValueError):money(value)
    def test_quoted_vendor(self):
        data=SAMPLES['invoices'].replace('Atlas Cloud','"Atlas, Cloud"')
        self.assertEqual(parse_csv(data,'invoices')[2]['vendor'],'Atlas, Cloud')
    def test_bad_schema_and_date(self):
        for text in ['wrong,header\n',SAMPLES['invoices'].replace('2026-09-01','2026-02-30')]:
            with self.assertRaises(ValueError):parse_csv(text,'invoices')
    def test_reference_boundaries(self):
        self.assertTrue(near('inv1234','inv123a'));self.assertFalse(near('inv1234','inv12ab'));self.assertFalse(near('123','124'))
class WorkerTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'.test-work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.test-work');os.environ['LEDGERGUARD_DB']=self.temp.name+'/test.db';store.initialize()
    def tearDown(self):self.temp.cleanup()
    def test_job_and_case_audit(self):
        job=store.submit(SAMPLES);self.assertEqual(store.status(job)['state'],'queued');store.tick();self.assertEqual(store.status(job)['state'],'complete')
        case=store.transition(job,'CASE-0001','investigating','Checked invoice scan')
        self.assertEqual(case['audit'][0]['previous'],'open')
        with self.assertRaises(ValueError):store.transition(job,'CASE-0001','resolved','')
        store.transition(job,'CASE-0001','resolved','Supplier confirmed credit note')
        with self.assertRaises(ValueError):store.transition(job,'CASE-0001','open','Reopen')
        self.assertEqual(len(store.status(job)['result']['cases'][0]['audit']),2)
    def test_retry_and_dead_letter(self):
        job=store.submit(SAMPLES)
        def fail(_):raise RuntimeError('synthetic failure')
        for attempt in range(3):
            with store.db() as c:c.execute('UPDATE jobs SET available=0 WHERE id=?',(job,))
            store.tick(fail)
        state=store.status(job);self.assertEqual(state['state'],'dead');self.assertEqual(state['attempts'],3)
    def test_worker_recovery(self):
        job=store.submit(SAMPLES)
        with store.db() as c:c.execute("UPDATE jobs SET state='running',attempts=1,lease=0 WHERE id=?",(job,))
        store.tick();self.assertEqual(store.status(job)['state'],'complete');self.assertEqual(store.status(job)['attempts'],2)
    def test_concurrent_claims(self):
        job=store.submit(SAMPLES)
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda _:store.tick(),range(4)))
        self.assertEqual(store.status(job)['attempts'],1)
    def test_invalid_not_queued(self):
        with self.assertRaises(ValueError):store.submit({})
        with store.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],0)
if __name__=='__main__':unittest.main()
