import json
from pathlib import Path
import secrets
import shutil
import tempfile
import unittest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.c2.access.routes import get_store,COOKIE
from app.c2.access.schemas import NewUser
from app.c2.access.store import Store,DEMO_FARM,verify_password,token_hash
from app.c2.microclimate.common.paths import BACKEND
from app.c2.microclimate.api import service as inference_service

PREFIX='/api/c2/access'


class AccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_runtimes=dict(inference_service._runtimes)
        cls.base=tempfile.TemporaryDirectory()
        cls.template=Path(cls.base.name)/'template.sqlite3'
        store=Store(cls.template)
        cls.passwords={name:secrets.token_urlsafe(20) for name in ('admin','researcher','viewer')}
        cls.ids={'admin':store.bootstrap('test_admin',cls.passwords['admin'])}
        for role in ('researcher','viewer'):
            cls.ids[role]=store.create_user(NewUser(username='test_'+role,password=cls.passwords[role],role=role))
        with store.db() as db:
            for role in ('researcher','viewer'):db.execute('INSERT INTO memberships VALUES(?,?)',(cls.ids[role],DEMO_FARM))

    @classmethod
    def tearDownClass(cls):
        inference_service._runtimes.clear();inference_service._runtimes.update(cls.previous_runtimes)
        cls.base.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'access.sqlite3'
        shutil.copy2(self.template,self.path);self.store=Store(self.path)
        app.dependency_overrides[get_store]=lambda:self.store
        self.client=TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',50000))
        self.csrf=''

    def tearDown(self):
        self.client.close();app.dependency_overrides.clear();self.temp.cleanup()

    def login(self,role='admin'):
        r=self.client.post(PREFIX+'/login',json={'username':'test_'+role,'password':self.passwords[role]})
        self.assertEqual(r.status_code,200,r.text);self.csrf=r.json()['csrf_token'];return r

    def write(self,path,body=None,method='POST'):
        return self.client.request(method,PREFIX+path,json=body,headers={'X-CSRF-Token':self.csrf})

    def farm(self):
        r=self.write('/farms',{'farm_name':'Test-only unlocated record','district':'Test-only metadata','crop_type':'Test crop'})
        self.assertEqual(r.status_code,201,r.text);return r.json()['farm_id']

    def test_unauthenticated_direct_requests_rejected(self):
        for path in ('/farms','/users','/nodes','/me'):
            self.assertEqual(self.client.get(PREFIX+path).status_code,401)
        self.assertEqual(self.client.post(PREFIX+'/farms',json={'farm_name':'x'}).status_code,401)

    def test_password_hash_and_protected_session_storage(self):
        r=self.login()
        self.assertIn('HttpOnly',r.headers['set-cookie']);self.assertIn('SameSite=strict',r.headers['set-cookie'])
        self.assertIn('Path=/api/c2;',r.headers['set-cookie']);self.assertEqual(r.headers['cache-control'],'no-store')
        token=self.client.cookies.get(COOKIE)
        with self.store.db() as db:
            row=db.execute('SELECT * FROM users WHERE id=?',(self.ids['admin'],)).fetchone()
            self.assertNotEqual(row['password_hash'],self.passwords['admin']);self.assertTrue(verify_password(self.passwords['admin'],row['password_hash']))
            self.assertEqual(db.execute('SELECT id_hash FROM sessions').fetchone()[0],token_hash(token))

    def test_no_default_users_or_coordinates_and_bootstrap_once(self):
        fresh=Store(Path(self.temp.name)/'empty.sqlite3');self.assertEqual(fresh.users(),[])
        with self.assertRaises(ValueError):self.store.bootstrap('another_admin',secrets.token_urlsafe(20))
        self.login();farms=self.client.get(PREFIX+'/farms').json()
        self.assertIsNone(farms[0]['latitude']);self.assertIsNone(farms[0]['longitude']);self.assertEqual(farms[0]['is_demo'],1)
        self.assertEqual({n['node_id'] for s in farms[0]['sites'] for n in s['nodes']},{'NODE_01','NODE_02'})

    def test_csrf_and_untrusted_origin_rejected(self):
        self.login()
        self.assertEqual(self.client.post(PREFIX+'/logout').status_code,403)
        self.assertEqual(self.client.get(PREFIX+'/farms',headers={'Origin':'https://untrusted.example'}).status_code,403)
        self.assertEqual(self.write('/logout').status_code,200)
        self.assertEqual(self.client.get(PREFIX+'/me').status_code,401)

    def test_local_only_host_and_remote_client_rejected(self):
        remote=TestClient(app,base_url='http://127.0.0.1:8000',client=('192.0.2.1',50000))
        self.assertEqual(remote.get(PREFIX+'/farms').status_code,403);remote.close()
        self.assertEqual(self.client.get(PREFIX+'/farms',headers={'host':'untrusted.example'}).status_code,403)

    def test_non_admin_cannot_manage_roles_and_researcher_cannot_create_farms(self):
        for role in ('researcher','viewer'):
            self.login(role)
            self.assertEqual(self.write('/users/'+self.ids['admin'],{'role':'viewer','active':True},'PUT').status_code,403)
            self.assertEqual(self.write('/farms',{'farm_name':'Test record','district':'Test','crop_type':'Test crop'}).status_code,201 if role=='viewer' else 403)
            self.assertEqual(self.client.get(PREFIX+'/users').status_code,403)

    def test_admin_can_create_update_farm_site_and_membership(self):
        self.login();farm=self.farm()
        changed=self.write('/farms/'+farm,{'farm_name':'Updated test-only record','district':'Test-only','crop_type':'Test crop','growth_stage':None},'PUT')
        self.assertEqual(changed.status_code,200,changed.text)
        r=self.write('/farms/'+farm+'/sites',{'site_name':'Unobserved test site'})
        self.assertEqual(r.status_code,201)
        site_id=r.json()['site_id']
        self.assertEqual(self.write(f'/farms/{farm}/sites/{site_id}',{'site_name':'Updated test site'},'PUT').status_code,200)
        self.assertEqual(self.write('/farms/'+farm+'/members/'+self.ids['viewer'],{'granted':True},'PUT').status_code,200)
        self.login('viewer');self.assertIn(farm,[f['farm_id'] for f in self.client.get(PREFIX+'/farms').json()])

    def test_admin_user_management_and_credentialed_put_preflight(self):
        self.login()
        response=self.write('/users',{'username':'temporary_created_user','password':secrets.token_urlsafe(20),'role':'researcher'})
        self.assertEqual(response.status_code,201,response.text)
        user_id=response.json()['user_id']
        self.assertEqual(self.write('/users/'+user_id,{'role':'viewer','active':False},'PUT').status_code,200)
        self.assertNotIn('password',self.client.get(PREFIX+'/users').text)
        cors=self.client.options(PREFIX+'/farms/test',headers={'Origin':'http://127.0.0.1:5173','Access-Control-Request-Method':'PUT','Access-Control-Request-Headers':'content-type,x-csrf-token'})
        self.assertEqual(cors.status_code,200,cors.text)
        self.assertEqual(cors.headers['access-control-allow-credentials'],'true')
        self.assertIn('PUT',cors.headers['access-control-allow-methods'])

    def test_other_farm_isolation_and_direct_id_guessing(self):
        self.login();farm=self.farm();self.login('viewer')
        self.assertNotIn(farm,[f['farm_id'] for f in self.client.get(PREFIX+'/farms').json()])
        for endpoint in ('history','forecasts'):
            self.assertEqual(self.client.get(f'{PREFIX}/farms/{farm}/{endpoint}',params={'site_id':'demo_site_node_01','node_id':'NODE_01'}).status_code,404)

    def test_membership_revocation_is_immediate(self):
        self.login();self.write(f'/farms/{DEMO_FARM}/members/{self.ids["viewer"]}',{'granted':False},'PUT')
        self.login('viewer');self.assertEqual(self.client.get(PREFIX+'/farms').json(),[])
        self.assertEqual(self.client.get(f'{PREFIX}/farms/{DEMO_FARM}/history',params={'site_id':'demo_site_node_01','node_id':'NODE_01'}).status_code,404)

    def test_coordinates_timezone_pair_and_demo_constraints(self):
        self.login();base={'farm_name':'Test-only metadata','district':'Test district','crop_type':'Test crop'}
        for extra in ({'latitude':91.,'longitude':0.},{'latitude':0.,'longitude':181.},{'latitude':1.},{'timezone':'not/a/zone'},{'latitude':True,'longitude':0.},{'is_demo':True,'latitude':0.,'longitude':0.},{'is_demo':True,'growth_stage':'Invented'}):
            r=self.write('/farms',{**base,**extra});self.assertEqual(r.status_code,422,r.text)
        r=self.write('/farms',{**base,'latitude':0.,'longitude':0.})
        self.assertEqual(r.status_code,201)  # Test-only coordinate validation, not an actual farm seed.

    def test_no_farm_node_cross_mapping_or_synthetic_relabel(self):
        self.login();farm=self.farm();site=self.write('/farms/'+farm+'/sites',{'site_name':'Test site'}).json()['site_id']
        self.assertEqual(self.write(f'/farms/{farm}/nodes/NODE_01',{'site_id':site},'PUT').status_code,422)
        self.assertEqual(self.write(f'/farms/{DEMO_FARM}/nodes/NODE_01',{'site_id':site},'PUT').status_code,404)
        self.assertEqual(self.client.get(f'{PREFIX}/farms/{DEMO_FARM}/history',params={'site_id':'demo_site_node_02','node_id':'NODE_01'}).status_code,404)

    def test_registered_real_node_has_no_silent_demo_fallback(self):
        self.login();farm=self.farm();site=self.write('/farms/'+farm+'/sites',{'site_name':'No-data site'}).json()['site_id']
        self.assertEqual(self.write('/nodes',{'node_id':'TEST_UNOBSERVED'}).status_code,201)
        self.assertEqual(self.write(f'/farms/{farm}/nodes/TEST_UNOBSERVED',{'site_id':site},'PUT').status_code,200)
        params={'site_id':site,'node_id':'TEST_UNOBSERVED'}
        self.assertEqual(self.client.get(f'{PREFIX}/farms/{farm}/history',params=params).status_code,409)
        self.assertEqual(self.write(f'/farms/{farm}/forecast',{**params,'model':'lstm'}).status_code,409)

    def test_farmer_can_run_assigned_forecast(self):
        self.login('viewer')
        self.assertEqual(self.write(f'/farms/{DEMO_FARM}/forecast',{'site_id':'demo_site_node_01','node_id':'NODE_01','model':'gru'}).status_code,200)

    def test_role_change_revokes_sessions_and_last_admin_is_retained(self):
        other=TestClient(app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',50001))
        self.assertEqual(other.post(PREFIX+'/login',json={'username':'test_researcher','password':self.passwords['researcher']}).status_code,200)
        self.login();self.assertEqual(self.write('/users/'+self.ids['admin'],{'role':'viewer','active':True},'PUT').status_code,409)
        self.assertEqual(self.write('/users/'+self.ids['researcher'],{'role':'viewer','active':True},'PUT').status_code,200)
        self.assertEqual(other.get(PREFIX+'/me').status_code,401);other.close()
        self.login('researcher');self.assertEqual(self.client.get(PREFIX+'/me').json()['user']['role'],'viewer')
        with self.store.db() as db:db.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.client.get(PREFIX+'/me').status_code,401)

    def test_login_throttle_generic_errors_and_password_validation_redaction(self):
        for _ in range(5):
            r=self.client.post(PREFIX+'/login',json={'username':'unknown_account','password':secrets.token_urlsafe(10)})
            self.assertEqual(r.status_code,401);self.assertEqual(r.json()['detail'],'Invalid username or password')
        self.assertEqual(self.client.post(PREFIX+'/login',json={'username':'unknown_account','password':'x'}).status_code,429)
        secret=secrets.token_urlsafe(150)
        r=self.client.post(PREFIX+'/login',json={'username':'test_admin','password':secret})
        self.assertEqual(r.status_code,422);self.assertNotIn(secret,r.text)

    def test_payload_limit_and_private_no_store(self):
        r=self.client.post(PREFIX+'/login',content=b'x'*17000,headers={'content-type':'application/json'})
        self.assertEqual(r.status_code,413);self.assertEqual(r.headers['cache-control'],'no-store')

    def test_sitewide_research_apis_require_authentication(self):
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input').status_code,401)
        for path in ('/api/c2/yield/predict','/api/c2/microclimate/forecast'):
            self.assertEqual(self.client.post(path,json={}).status_code,401)

    def test_viewer_cannot_bypass_farm_scope_through_legacy_apis(self):
        self.login('viewer')
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input').status_code,403)
        self.assertEqual(self.client.post('/api/c2/microclimate/forecast',json={},headers={'X-CSRF-Token':self.csrf}).status_code,403)
        self.assertEqual(self.client.post('/api/c2/yield/predict',json={},headers={'X-CSRF-Token':self.csrf}).status_code,422)
        self.assertEqual(self.client.get(PREFIX+'/farms').status_code,200)

    def test_researcher_access_and_csrf_on_all_prediction_mutations(self):
        self.login('researcher')
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input').status_code,200)
        for path in ('/api/c2/yield/predict','/api/c2/microclimate/forecast'):
            self.assertEqual(self.client.post(path,json={}).status_code,403)
            self.assertEqual(self.client.post(path,json={},headers={'X-CSRF-Token':self.csrf}).status_code,422)
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input',headers={'Origin':'https://untrusted.example'}).status_code,403)

    def test_existing_access_only_cookie_migrates_without_replacing_session(self):
        self.login();token=self.client.cookies.get(COOKIE)
        self.client.cookies.clear();self.client.cookies.set(COOKIE,token,domain='127.0.0.1',path='/api/c2/access')
        with self.store.db() as db:before=db.execute('SELECT expires FROM sessions WHERE id_hash=?',(token_hash(token),)).fetchone()[0]
        response=self.client.get(PREFIX+'/me');self.assertEqual(response.status_code,200)
        self.assertEqual(self.client.cookies.get(COOKIE),token)
        self.assertTrue(any(cookie.path=='/api/c2' for cookie in self.client.cookies.jar))
        self.assertFalse(any(cookie.path=='/api/c2/access' for cookie in self.client.cookies.jar))
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input').status_code,200)
        with self.store.db() as db:self.assertEqual(db.execute('SELECT expires FROM sessions WHERE id_hash=?',(token_hash(token),)).fetchone()[0],before)

    def test_refresh_restores_identity_without_extending_absolute_expiry(self):
        self.login('researcher');token=self.client.cookies.get(COOKIE)
        with self.store.db() as db:before=db.execute('SELECT expires FROM sessions').fetchone()[0]
        for _ in range(2):
            response=self.client.get(PREFIX+'/me');self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['user']['id'],self.ids['researcher'])
        with self.store.db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT expires FROM sessions').fetchone()[0],before)
        self.assertEqual(Store(self.path).principal(token)['id'],self.ids['researcher'])

    def test_logout_revokes_session_for_entire_c2_api(self):
        self.login();self.assertEqual(self.write('/logout').status_code,200)
        self.assertEqual(self.client.get(PREFIX+'/me').status_code,401)
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input').status_code,401)
        self.assertEqual(self.client.post('/api/c2/yield/predict',json={}).status_code,401)

    def test_expired_session_is_rejected_by_all_research_apis(self):
        self.login()
        with self.store.db() as db:db.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.client.get(PREFIX+'/me').status_code,401)
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input').status_code,401)
        self.assertEqual(self.client.post('/api/c2/yield/predict',json={},headers={'X-CSRF-Token':self.csrf}).status_code,401)

    def test_wrong_password_rejects_existing_and_unknown_users_identically(self):
        responses=[]
        for name in ('test_admin','does_not_exist'):
            response=self.client.post(PREFIX+'/login',json={'username':name,'password':secrets.token_urlsafe(20)})
            self.assertEqual(response.status_code,401);responses.append(response.json())
        self.assertEqual(responses[0],responses[1])

    def test_registration_least_privilege_and_real_login(self):
        password=secrets.token_urlsafe(20)
        headers={'Origin':'http://127.0.0.1:5173'}
        body={'username':'new_farmer','password':password}
        self.assertEqual(self.client.post(PREFIX+'/register',json=body).status_code,403)
        self.assertEqual(self.client.post(PREFIX+'/register',json={**body,'role':'admin'},headers=headers).status_code,422)
        response=self.client.post(PREFIX+'/register',json=body,headers=headers)
        self.assertEqual(response.status_code,201,response.text)
        self.assertNotIn(password,response.text)
        login=self.client.post(PREFIX+'/login',json=body)
        self.assertEqual(login.status_code,200)
        self.assertEqual(login.json()['user']['role'],'viewer')
        self.assertEqual(self.client.get(PREFIX+'/farms').json(),[])
        self.assertEqual(self.client.get(PREFIX+'/users').status_code,403)
        self.assertEqual(self.client.post(PREFIX+'/register',json=body,headers=headers).status_code,409)

    def test_registration_throttle_and_password_validation(self):
        headers={'Origin':'http://127.0.0.1:5173'}
        short=secrets.token_urlsafe(3)
        response=self.client.post(PREFIX+'/register',json={'username':'new_farmer','password':short},headers=headers)
        self.assertEqual(response.status_code,422);self.assertNotIn(short,response.text)
        # Existing-name failures must also consume the registration allowance.
        body={'username':'test_admin','password':secrets.token_urlsafe(20)}
        for _ in range(5):self.assertEqual(self.client.post(PREFIX+'/register',json=body,headers=headers).status_code,409)
        self.assertEqual(self.client.post(PREFIX+'/register',json=body,headers=headers).status_code,429)

    def test_farmer_owns_created_farm_and_can_edit_only_own_metadata(self):
        self.login('viewer');farm=self.farm()
        own=next(f for f in self.client.get(PREFIX+'/farms').json() if f['farm_id']==farm)
        self.assertTrue(own['owned']);self.assertTrue(own['assigned']);self.assertEqual(own['sites'],[])
        changed={'farm_name':'Changed own farm','district':'Test district','crop_type':'Test crop','latitude':0.,'longitude':0.}
        self.assertEqual(self.write('/farms/'+farm,changed,'PUT').status_code,200)
        self.assertEqual(self.write('/farms/'+DEMO_FARM,changed,'PUT').status_code,403)
        self.assertEqual(self.write('/farms/'+farm+'/sites',{'site_name':'Unauthorized site'}).status_code,403)
        self.assertEqual(self.write('/farms/'+farm+'/nodes/NODE_01',{'site_id':'demo_site_node_01'},'PUT').status_code,403)
        self.assertEqual(self.write('/farms',{**changed,'is_demo':True}).status_code,403)
        self.assertEqual(self.write('/farms',{**changed,'latitude':91.}).status_code,422)
        self.assertEqual(self.client.delete(PREFIX+'/farms/'+farm,headers={'X-CSRF-Token':self.csrf}).status_code,405)

    def test_unassigned_farmer_cannot_read_edit_or_execute_another_farm(self):
        outsider=self.store.create_user(NewUser(username='unassigned_farmer',password=secrets.token_urlsafe(20),role='viewer'))
        token=self.store.login('test_viewer',self.passwords['viewer'],'test-owner')
        from app.c2.access.store import csrf_token
        self.client.cookies.set(COOKIE,token,domain='127.0.0.1',path='/api/c2')
        self.csrf=csrf_token(token);farm=self.farm()
        # Move the test identity's session to a different valid, unassigned user.
        with self.store.db() as db:db.execute('UPDATE sessions SET user_id=? WHERE id_hash=?',(outsider,token_hash(token)))
        self.assertEqual(self.client.get(PREFIX+'/farms').json(),[])
        for farm_id in (farm,DEMO_FARM):
            params={'site_id':'demo_site_node_01','node_id':'NODE_01'}
            self.assertEqual(self.client.get(f'{PREFIX}/farms/{farm_id}/history',params=params).status_code,404)
            self.assertEqual(self.write(f'/farms/{farm_id}/forecast',{**params,'model':'lstm'}).status_code,404)
            self.assertEqual(self.write('/farms/'+farm_id,{'farm_name':'Unauthorized','district':'Test','crop_type':'Test crop'},'PUT').status_code,404)

    def test_farmer_cannot_elevate_role_or_assign_memberships(self):
        self.login('viewer')
        self.assertEqual(self.write('/users/'+self.ids['viewer'],{'role':'admin','active':True},'PUT').status_code,403)
        self.assertEqual(self.write(f'/farms/{DEMO_FARM}/members/{self.ids["viewer"]}',{'granted':True},'PUT').status_code,403)
        self.assertEqual(self.write('/nodes',{'node_id':'UNAUTHORIZED_NODE'}).status_code,403)

    def test_farmer_no_data_forecast_does_not_fall_back_to_sample(self):
        self.login();farm=self.farm()
        site=self.write('/farms/'+farm+'/sites',{'site_name':'No observations'}).json()['site_id']
        self.write('/nodes',{'node_id':'UNOBSERVED_NODE'})
        self.write(f'/farms/{farm}/nodes/UNOBSERVED_NODE',{'site_id':site},'PUT')
        self.write(f'/farms/{farm}/members/{self.ids["viewer"]}',{'granted':True},'PUT')
        self.login('viewer')
        params={'site_id':site,'node_id':'UNOBSERVED_NODE'}
        self.assertEqual(self.client.get(f'{PREFIX}/farms/{farm}/history',params=params).status_code,409)
        self.assertEqual(self.write(f'/farms/{farm}/forecast',{**params,'model':'gru'}).status_code,409)

    def test_farmer_yield_models_authentication_and_csrf(self):
        self.login('viewer')
        self.assertEqual(self.client.post('/api/c2/yield/predict',json={}).status_code,403)
        self.assertEqual(self.client.post('/api/c2/yield/predict',json={},headers={'X-CSRF-Token':self.csrf}).status_code,422)
        body={'plant_height_cm':60,'main_branches':5,'leaf_length_cm':8,'leaf_breadth_cm':3,'days_to_50pct_flowering':45}
        response=self.client.post('/api/c2/yield/predict',json=body,headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['unit'],'g/plant')
        self.assertEqual(response.json()['predicted_yield_g_per_plant'],275.59)

    def test_unassigned_researcher_cannot_retrieve_legacy_sample_history(self):
        with self.store.db() as db:db.execute('DELETE FROM memberships WHERE user_id=?',(self.ids['researcher'],))
        self.login('researcher')
        self.assertEqual(self.client.get('/api/c2/microclimate/demo-input').status_code,404)

    def test_real_protected_inference_all_models_nodes_and_saved_viewer_results(self):
        self.login('viewer')
        maximum=0.
        for node in ('NODE_01','NODE_02'):
            site='demo_site_'+node.lower()
            history=self.client.get(f'{PREFIX}/farms/{DEMO_FARM}/history',params={'site_id':site,'node_id':node})
            self.assertEqual(history.status_code,200,history.text);self.assertEqual(len(history.json()['request']['observations']),336)
            for model in ('lstm','gru','attention_bilstm'):
                r=self.write(f'/farms/{DEMO_FARM}/forecast',{'site_id':site,'node_id':node,'model':model})
                self.assertEqual(r.status_code,200,r.text)
                result=r.json()['response'];self.assertEqual(len(result['predictions']),168)
                actual=np.array([[p[k] for k in result['target_order']] for p in result['predictions']])
                self.assertTrue(np.isfinite(actual).all())
                with np.load(BACKEND/f'experiments/c2/microclimate/{model}_v1/test_predictions_{node}.npz',allow_pickle=False) as saved:
                    expected=saved['predictions_original_units'][0]
                delta=float(np.max(np.abs(actual-expected)));maximum=max(maximum,delta)
                self.assertLessEqual(delta,1e-4)
        self.login('viewer')
        saved=self.client.get(f'{PREFIX}/farms/{DEMO_FARM}/forecasts',params={'site_id':'demo_site_node_01','node_id':'NODE_01'})
        self.assertEqual(saved.status_code,200);self.assertEqual(len(saved.json()),3)
        self.assertEqual(len(saved.json()[0]['response']['predictions']),168)
        print('PROTECTED_API_SAVED_OUTPUT_MAX_DIFFERENCE',maximum)


if __name__=='__main__':unittest.main()
