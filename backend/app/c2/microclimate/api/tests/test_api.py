"""Real FastAPI/CPU-checkpoint integration, plus explicit error-path injection."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timedelta
import json
import os
import secrets
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from ...common.paths import BACKEND,SCALED_OUTPUT,digest
from ...preprocessing.pipeline import LABEL,TARGETS
from .. import service
from ..http import MAX_REQUEST_BYTES
from ..schemas import ForecastRequest
from app.c2.access.routes import get_store
from app.c2.access.store import Store


class ForecastAPITests(unittest.TestCase):
    consistency={}

    @classmethod
    def setUpClass(cls):
        cls.auth_directory=tempfile.TemporaryDirectory(prefix='c2-api-auth-')
        cls.auth_store=Store(Path(cls.auth_directory.name)/'access.sqlite3')
        password=secrets.token_urlsafe(24)
        cls.auth_store.bootstrap('api_test_admin',password)
        app.dependency_overrides[get_store]=lambda:cls.auth_store
        cls.client=TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',50000));cls.client.__enter__()
        login=cls.client.post('/api/c2/access/login',json={'username':'api_test_admin','password':password})
        if login.status_code!=200:raise AssertionError('Test authentication failed')
        cls.client.headers['X-CSRF-Token']=login.json()['csrf_token']
        cls.requests={}
        for node in ('NODE_01','NODE_02'):
            response=cls.client.get('/api/c2/microclimate/demo-input',params={'node_id':node})
            if response.status_code!=200:raise AssertionError(response.text)
            cls.requests[node]=response.json()['request']
        import keras
        # Actual loads/inference are executed; wraps records calls without replacing outputs.
        with patch.object(keras.models,'load_model',wraps=keras.models.load_model) as spy:
            with ThreadPoolExecutor(max_workers=2) as pool:
                runtimes=list(pool.map(lambda _:service.get_runtime('lstm'),range(2)))
            cls.concurrent_identity=runtimes[0] is runtimes[1]
            cls.first_selection=set(service._runtimes)
            cls.responses={}
            for model in ('lstm','gru','attention_bilstm'):
                for node in ('NODE_01','NODE_02'):
                    request=deepcopy(cls.requests[node]);request['model']=model
                    response=cls.client.post('/api/c2/microclimate/forecast',json=request)
                    if response.status_code!=200:raise AssertionError(response.text)
                    cls.responses[model,node]=response.json()
            # Repeat a real HTTP inference after all three initial loads.
            cls.client.post('/api/c2/microclimate/forecast',json=cls.requests['NODE_01']).raise_for_status()
            cls.load_count=spy.call_count

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None,None,None)
        app.dependency_overrides.clear();cls.auth_directory.cleanup()

    def request(self):
        return deepcopy(self.requests['NODE_01'])

    def reject(self,request,status=422):
        response=self.client.post('/api/c2/microclimate/forecast',json=request)
        self.assertEqual(response.status_code,status,response.text)
        self.assertNotIn('Traceback',response.text)
        self.assertNotIn(str(BACKEND),response.text)
        return response

    def test_app_health_openapi_and_yield_are_preserved(self):
        self.assertEqual(self.client.get('/health').json()['status'],'ok')
        schema=self.client.get('/openapi.json').json()
        self.assertIn('/api/c2/microclimate/forecast',schema['paths'])
        result=self.client.post('/api/c2/yield/predict',json=dict(plant_height_cm=60,main_branches=5,
            leaf_length_cm=8,leaf_breadth_cm=3,days_to_50pct_flowering=45))
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['predicted_yield_g_per_plant'],275.59)
        self.assertEqual(self.client.post('/api/c2/yield/predict',json={}).status_code,422)

    def test_all_models_two_nodes_finite_shape_and_provenance(self):
        for (model,node),response in self.responses.items():
            with self.subTest(model=model,node=node):
                self.assertEqual((response['model'],response['node_id']),(model,node))
                self.assertEqual(len(response['predictions']),168)
                values=np.array([[step[t] for t in TARGETS] for step in response['predictions']])
                self.assertEqual(values.shape,(168,3));self.assertTrue(np.isfinite(values).all())
                self.assertEqual(tuple(response['feature_order']),TARGETS)
                self.assertEqual(tuple(response['target_order']),TARGETS)
                self.assertEqual(response['evaluation_label'],LABEL)
                self.assertEqual(response['provenance']['scaler_sha256'],digest(SCALED_OUTPUT/'scalers.json'))
                self.assertIn('not calibrated',response['units'][TARGETS[0]])
                self.assertNotIn(str(BACKEND),json.dumps(response))

    def test_timestamp_alignment_and_cumulative_slices(self):
        for response in self.responses.values():
            origin=datetime.fromisoformat(response['forecast_origin'])
            self.assertEqual(origin,datetime.fromisoformat(response['history']['end']))
            for hour,step in enumerate(response['predictions'],1):
                self.assertEqual(step['lead_hour'],hour)
                self.assertEqual(datetime.fromisoformat(step['timestamp']),origin+timedelta(hours=hour))
            for item in response['slices']:
                h=item['hours'];self.assertEqual(item['start_index'],0);self.assertEqual(item['end_index_exclusive'],h)
                self.assertEqual(item['first_timestamp'],response['predictions'][0]['timestamp'])
                self.assertEqual(item['last_timestamp'],response['predictions'][h-1]['timestamp'])

    def test_exact_prepared_input_tensor_and_history_mask(self):
        for node in self.requests:
            request=ForecastRequest.model_validate(self.requests[node])
            x,valid=service.prepare_history(request,service.get_runtime('lstm').input_scaler)
            with np.load(SCALED_OUTPUT/f'windows_test_{node}.npz',allow_pickle=False) as source:
                np.testing.assert_array_equal(x,source['X'][:1])
                np.testing.assert_array_equal(valid,source['history_valid_mask'][0])

    def test_api_predictions_match_existing_cli_and_test_outputs(self):
        # Batch-1 API versus batch-16 saved CLI: allow 1e-4 original-unit float32 rounding.
        for (model,node),response in self.responses.items():
            folder=service.MODEL_SPECS[model][0]
            root=BACKEND/'experiments/c2/microclimate'/folder
            filename='inference_check_NODE_01.npz' if node=='NODE_01' else f'test_predictions_{node}.npz'
            with np.load(root/filename,allow_pickle=False) as saved:
                expected=saved['predictions_original_units'][0]
                actual=np.array([[step[t] for t in TARGETS] for step in response['predictions']])
                np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-4)
                self.consistency[f'{model}_{node}']=float(np.max(np.abs(actual-expected)))
        print('API_CONSISTENCY '+json.dumps(self.consistency),flush=True)

    def test_lazy_cache_only_loads_selected_models_once_and_is_concurrent_safe(self):
        self.assertTrue(self.concurrent_identity)
        self.assertEqual(self.first_selection,{'lstm'})
        self.assertEqual(self.load_count,3)
        self.assertEqual(set(service._runtimes),{'lstm','gru','attention_bilstm'})

    def test_demo_never_exposes_future_labels_or_predictions(self):
        response=self.client.get('/api/c2/microclimate/demo-input')
        demo=response.json();self.assertEqual(response.status_code,200)
        self.assertFalse(demo['demo']['ground_truth_included']);self.assertTrue(demo['demo']['prepared_tensor_match'])
        self.assertEqual(len(demo['request']['observations']),336)
        for forbidden in ('y','target_valid_mask','predictions','actual_original_units'):
            self.assertNotIn(forbidden,demo['request']);self.assertNotIn(forbidden,demo['demo'])
        self.assertEqual(demo['request']['data_origin'],'synthetic')
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input',params={'sample_index':811}).status_code,422)

    def test_length_335_and_337_rejected(self):
        request=self.request();request['observations'].pop();self.reject(request)
        request=self.request();request['observations'].append(request['observations'][-1]);self.reject(request)

    def test_missing_and_non_numeric_features_rejected(self):
        for value in (None,'27.5',True):
            request=self.request();request['observations'][10]['air_temperature_c']=value;self.reject(request)
        request=self.request();del request['observations'][10]['air_temperature_c'];self.reject(request)

    def test_nonfinite_features_rejected_without_echoing_input(self):
        for value in (float('nan'),float('inf'),float('-inf')):
            request=self.request();request['observations'][10]['air_temperature_c']=value
            response=self.client.post('/api/c2/microclimate/forecast',content=json.dumps(request),headers={'Content-Type':'application/json'})
            self.assertEqual(response.status_code,422)
            self.assertTrue(all('input' not in error and 'ctx' not in error for error in response.json()['detail']))

    def test_duplicates_gaps_and_out_of_order_rejected(self):
        for delta in (0,2,-1):
            request=self.request();time=datetime.fromisoformat(request['observations'][9]['timestamp'])
            request['observations'][10]['timestamp']=(time+timedelta(hours=delta)).isoformat();self.reject(request)

    def test_naive_or_nonhourly_timestamps_rejected(self):
        request=self.request();request['observations'][0]['timestamp']='2025-11-07T00:00:00';self.reject(request)
        request=self.request();request['observations'][0]['timestamp']='2025-11-07T00:01:00+05:30';self.reject(request)
        request=self.request();request['observations'][0]['timestamp']=1762453800;self.reject(request)

    def test_utc_offsets_normalize_to_training_timezone(self):
        from datetime import timezone
        request=self.request()
        for row in request['observations']:
            row['timestamp']=datetime.fromisoformat(row['timestamp']).astimezone(timezone.utc).isoformat()
        parsed=ForecastRequest.model_validate(request)
        self.assertEqual(parsed.observations[0].timestamp.utcoffset(),timedelta(hours=5,minutes=30))
        x,_=service.prepare_history(parsed,service.get_runtime('lstm').input_scaler)
        with np.load(SCALED_OUTPUT/'windows_test_NODE_01.npz',allow_pickle=False) as z:np.testing.assert_array_equal(x,z['X'][:1])

    def test_future_labels_unknown_weather_and_wrong_origin_rejected(self):
        request=self.request();request['future_targets']=[[1,2,3]];self.reject(request)
        request=self.request();request['observations'][0]['forecast_air_temp_max_c_next_24h']=33;self.reject(request)
        request=self.request();request['forecast_origin']=request['observations'][-2]['timestamp'];self.reject(request)

    def test_supported_model_and_node_identifiers(self):
        request=self.request();request['model']='other';self.reject(request)
        request=self.request();request['node_id']='REAL_FIELD';self.reject(request)

    def test_quality_invalid_anomalous_imputed_rows_use_only_past(self):
        variants=[dict(record_status='INVALID',is_anomaly=False,is_imputed=False,imputed_fields=''),
                  dict(record_status='WARN',is_anomaly=True,is_imputed=False,imputed_fields=''),
                  dict(record_status='WARN',is_anomaly=False,is_imputed=True,imputed_fields='air_temperature_c')]
        for metadata in variants:
            request=self.request();row=request['observations'][10];row.update(metadata)
            row.update(soil_moisture_avg_index=999.,air_temperature_c=999.,relative_humidity_pct=99.)
            parsed=ForecastRequest.model_validate(request)
            x,valid=service.prepare_history(parsed,service.get_runtime('lstm').input_scaler)
            self.assertFalse(valid[10]);np.testing.assert_array_equal(x[:,10,:],x[:,9,:])

    def test_clean_warn_retained_without_quality_score_threshold(self):
        request=self.request();row=request['observations'][0]
        row.update(record_status='WARN',is_anomaly=False,is_imputed=False,imputed_fields='',quality_score=0.)
        _,valid=service.prepare_history(ForecastRequest.model_validate(request),service.get_runtime('lstm').input_scaler)
        self.assertTrue(valid[0])

    def test_leading_untrusted_history_is_rejected(self):
        request=self.request();request['observations'][0]['record_status']='INVALID'
        response=self.reject(request);self.assertEqual(response.json()['detail']['code'],'invalid_history')

    def test_quality_metadata_consistency_and_physical_ranges(self):
        for updates in [dict(is_imputed=True),dict(is_anomaly=True),dict(imputed_fields='air_temperature_c'),
                        dict(relative_humidity_pct=101),dict(soil_moisture_avg_index=-1),dict(quality_score=2)]:
            request=self.request();request['observations'][0].update(updates);self.reject(request)

    def test_omitted_quality_is_explicit_caller_assertion(self):
        request=self.request()
        request['data_origin']='user_supplied_unverified'
        for row in request['observations']:
            for key in ('record_status','is_anomaly','is_imputed','imputed_fields','quality_score'):row.pop(key,None)
        parsed=ForecastRequest.model_validate(request)
        _,valid=service.prepare_history(parsed,service.get_runtime('lstm').input_scaler)
        self.assertTrue(valid.all());self.assertIn('caller assertions',service.QUALITY_POLICY)
        response=self.client.post('/api/c2/microclimate/forecast',json=request)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['history']['quality_metadata_rows'],0)
        self.assertEqual(response.json()['provenance']['declared_input_origin'],'user_supplied_unverified')

    def test_request_size_limit_declared_and_streamed(self):
        for content in (b' '*(MAX_REQUEST_BYTES+1),iter([b' '*MAX_REQUEST_BYTES,b' '])):
            response=self.client.post('/api/c2/microclimate/forecast',content=content,headers={'Content-Type':'application/json'})
            self.assertEqual(response.status_code,413);self.assertEqual(response.json()['detail']['code'],'request_too_large')

    def test_unavailable_artifacts_return_safe_503(self):
        runtime=service._runtimes.pop('lstm')
        request=self.request();request['model']='lstm'
        try:
            with patch.dict(service.MODEL_SPECS,{'lstm':('missing_checkpoint','missing.keras',service.MODEL_SPECS['lstm'][2],13027)}),self.assertLogs(service.logger,level='ERROR'):
                response=self.reject(request,503)
                self.assertEqual(response.json()['detail']['code'],'model_unavailable')
        finally:service._runtimes['lstm']=runtime

    def test_inference_failure_returns_safe_500(self):
        class BrokenModel:
            def __call__(self,*args,**kwargs):raise RuntimeError('C:\\private\\checkpoint.keras')
        runtime=service.get_runtime('attention_bilstm')
        with patch.object(runtime,'model',BrokenModel()),self.assertLogs(service.logger,level='ERROR'):
            response=self.reject(self.request(),500)
            self.assertEqual(response.json()['detail']['code'],'forecast_failed')
            self.assertNotIn('private',response.text)

    def test_startup_is_lazy_and_paths_do_not_depend_on_cwd(self):
        script="""import os,sys,secrets
os.chdir(sys.argv[1])
from fastapi.testclient import TestClient
from app.main import app
from app.c2.access.store import Store
from app.c2.access.routes import get_store
from pathlib import Path
store=Store(Path(sys.argv[1])/'temporary_access.sqlite3')
password=secrets.token_urlsafe(24)
store.bootstrap('cwd_test_admin',password)
app.dependency_overrides[get_store]=lambda:store
assert 'tensorflow' not in sys.modules
with TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',50000)) as client:
 login=client.post('/api/c2/access/login',json={'username':'cwd_test_admin','password':password})
 assert login.status_code==200
 client.headers['X-CSRF-Token']=login.json()['csrf_token']
 assert client.get('/health').status_code==200
 d=client.get('/api/c2/microclimate/demo-input',params={'model':'lstm'})
 assert d.status_code==200,d.text
 assert 'tensorflow' not in sys.modules
 r=client.post('/api/c2/microclimate/forecast',json=d.json()['request'])
 assert r.status_code==200,r.text
 assert len(r.json()['predictions'])==168
"""
        with tempfile.TemporaryDirectory(prefix='c2-api-cwd-') as directory:
            result=subprocess.run([str(BACKEND/'.venv/Scripts/python.exe'),'-B','-c',script,directory],
                                  cwd=directory,env=dict(os.environ,PYTHONPATH=str(BACKEND),TF_CPP_MIN_LOG_LEVEL='2'),
                                  capture_output=True,text=True,encoding='utf-8',errors='replace')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main(verbosity=2)
