import unittest
import json
from unittest.mock import patch
from main import profile, kind, _date, mock_map, MapItem, deterministic, transform, validate_final, openai_map

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{"CustomerID":"A1","Full Name":"Avery Morgan","email_address":"avery@example.com","DOB":"02/19/1991"},{"CustomerID":"A1","Full Name":"Jordan Lee","email_address":"bad","DOB":"nonsense"}]
    def test_profiling_nulls_and_types(self):
        rows=[{"email":"a@b.com","phone":"4155550123"},{"email":"","phone":""}]
        p={x['column']:x for x in profile(rows)}
        self.assertEqual(p['email']['null_pct'],50.0); self.assertEqual(p['email']['data_type'],'email')
    def test_type_inference_and_date(self):
        self.assertEqual(kind(['01/02/2020','2021-03-04']),'date'); self.assertEqual(_date('02/19/1991'),'1991-02-19')
    def test_mapping_and_deterministic_validation(self):
        p=profile(self.rows); mapped=mock_map(list(self.rows[0]),p)
        self.assertIn(['first_name','last_name'],[m.target_fields for m in mapped])
        email=MapItem(source_column='email_address',target_fields=['email'],confidence=.9,reason='test')
        self.assertTrue(deterministic(self.rows,email)['issues'])
        ident=MapItem(source_column='CustomerID',target_fields=['customer_id'],confidence=.9,reason='test')
        self.assertIn('duplicate',deterministic(self.rows,ident)['issues'][0])
    def test_transformation_and_final_validation(self):
        run={'rows':self.rows,'decisions':[{'source_column':'Full Name','target_fields':['first_name','last_name'],'status':'approved'},{'source_column':'DOB','target_fields':['date_of_birth'],'status':'approved'}]}
        data,errors=transform(run)
        self.assertEqual(data[0]['first_name'],'Avery'); self.assertEqual(data[0]['date_of_birth'],'1991-02-19'); self.assertTrue(errors)
        val=validate_final(data); self.assertEqual(val['rows_processed'],2); self.assertGreater(val['missing_required_values'],0); self.assertEqual(val['invalid_dates'],1)
    def test_openai_payload_is_compact_and_structured(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self): return json.dumps({'choices':[{'message':{'content':json.dumps({'mappings':[{'source_column':'email','target_fields':['email'],'confidence':.98,'reason':'Email column'}]})}}]}).encode()
        p=[{'column':'email','data_type':'email','null_pct':0,'unique_pct':100,'samples':['person@example.com']*8}]
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-key'}), patch('main.urllib.request.urlopen',return_value=Response()) as call:
            mappings,provider=openai_map(['email'],p)
        sent=json.loads(call.call_args.args[0].data)['messages'][1]['content']
        payload=json.loads(sent)
        self.assertEqual(provider,'openai'); self.assertEqual(mappings[0].target_fields,['email'])
        self.assertEqual(len(payload['profiling'][0]['samples']),5)
        self.assertEqual(payload['profiling'][0]['samples'][0],'[masked-email]')
        self.assertNotIn('rows',payload)
    def test_openai_invalid_structured_output_fails_safely(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self): return b'{"choices":[{"message":{"content":"not-json"}}]}'
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-key'}), patch('main.urllib.request.urlopen',return_value=Response()):
            with self.assertRaises(Exception) as caught: openai_map(['email'],[])
        self.assertEqual(caught.exception.status_code,502)

if __name__=='__main__': unittest.main()
