import json
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from main import app, RUNS

class ApiWorkflowTests(unittest.TestCase):
    def setUp(self):
        RUNS.clear()
        self.client=TestClient(app)
        self.csv=Path(__file__).parents[1].joinpath('data','sample_customer_data.csv').read_bytes()

    def test_complete_review_transform_and_export(self):
        health=self.client.get('/api/health')
        self.assertEqual(health.status_code,200)
        cors=self.client.options('/api/upload',headers={'Origin':'http://127.0.0.1:3000','Access-Control-Request-Method':'POST'})
        self.assertEqual(cors.headers.get('access-control-allow-origin'),'http://127.0.0.1:3000')
        uploaded=self.client.post('/api/upload',files={'file':('sample.csv',self.csv,'text/csv')})
        self.assertEqual(uploaded.status_code,200,uploaded.text)
        u=uploaded.json(); self.assertEqual(u['rows'],10); self.assertEqual(u['profile'][0]['column'],'CustomerID')
        phone_profile=next(p for p in u['profile'] if p['column']=='Phone #')
        self.assertGreater(phone_profile['null_pct'],0)
        run_id=u['run_id']
        mapped=self.client.post(f'/api/{run_id}/map')
        self.assertEqual(mapped.status_code,200,mapped.text)
        m=mapped.json(); self.assertEqual(m['provider'],'mock')
        by={x['source_column']:x for x in m['mappings']}
        self.assertEqual(by['Full Name']['status'],'approved')
        self.assertEqual(by['acct_status']['status'],'needs_review')
        self.assertTrue(by['email_address']['validation']['issues'])
        # Explicit human edits alter the resulting target field and status gates.
        decisions=[]
        for item in m['mappings']:
            fields=item['target_fields']; status=item['status']
            if item['source_column']=='City': fields=['address']; status='approved'
            if item['source_column'] in ('CustomerID','email_address','DOB'): status='approved'
            if item['source_column']=='acct_status': status='rejected'
            if item['source_column']=='Street Address': status='ignored'
            decisions.append({'source_column':item['source_column'],'target_fields':fields,'status':status})
        collisions=[dict(d) for d in decisions]
        for d in collisions:
            if d['source_column'] in ('City','Zip'):
                d['target_fields']=['postal_code']; d['status']='approved'
        conflict=self.client.post(f'/api/{run_id}/review',json={'decisions':collisions})
        self.assertEqual(conflict.status_code,409)
        reviewed=self.client.post(f'/api/{run_id}/review',json={'decisions':decisions})
        self.assertEqual(reviewed.status_code,200,reviewed.text)
        transformed=self.client.post(f'/api/{run_id}/transform')
        self.assertEqual(transformed.status_code,200,transformed.text)
        t=transformed.json(); row=t['preview'][0]
        self.assertEqual(row['first_name'],'Avery'); self.assertEqual(row['address'],'San Francisco')
        self.assertNotIn('account_status',row)
        self.assertEqual(t['validation']['rows_processed'],10)
        self.assertGreater(t['validation']['invalid_emails'],0)
        self.assertGreater(t['validation']['duplicate_ids'],0)
        self.assertGreater(t['validation']['invalid_dates'],0)
        self.assertGreater(len(t['transform_errors']),0)
        csv=self.client.get(f'/api/{run_id}/export.csv')
        self.assertEqual(csv.status_code,200); self.assertIn('address',csv.text)
        report=self.client.get(f'/api/{run_id}/report.json')
        self.assertEqual(report.status_code,200)
        r=report.json(); self.assertEqual(len(r['mappings']),len(decisions)); self.assertEqual(r['final_validation']['rows_processed'],10)
        self.assertTrue(any(x['source_column']=='acct_status' and not x['human_approved'] for x in r['mappings']))

if __name__=='__main__': unittest.main()
