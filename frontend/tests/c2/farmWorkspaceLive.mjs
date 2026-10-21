// Real authenticated HTTP + frontend client/selection verification, NOT browser automation.
import assert from 'node:assert/strict';
import { API_BASE, accessApi, selectionQuery, sessionFetch } from '../../src/services/c2/accessApi.js';
import { assignedFarmSelection, loadFarmWorkspace } from '../../src/services/c2/farmSelection.js';
import { MODELS, validateForecast, FEATURES, historicalSeries } from '../../src/services/c2/microclimateApi.js';
import { groupForecastDays } from '../../src/services/c2/forecastDays.js';
if (!process.env.C2_TEST_USERNAME || !process.env.C2_TEST_PASSWORD) throw new Error('Set test credentials privately; they are never printed.');
const originalFetch=globalThis.fetch;
let cookie='';
globalThis.fetch=async(url,options={})=>{
  const headers=new Headers(options.headers); headers.set('Origin','http://127.0.0.1:5173');
  if(cookie && String(url).startsWith(API_BASE+'/')) headers.set('Cookie',cookie);
  const response=await originalFetch(url,{...options,headers});
  for(const value of response.headers.getSetCookie()) if(value.startsWith('c2_local_session='))cookie=value.split(';',1)[0];
  return response;
};
try {
  await accessApi('/login',{method:'POST',body:{username:process.env.C2_TEST_USERNAME,password:process.env.C2_TEST_PASSWORD}});
  const {farms,selection}=assignedFarmSelection(await accessApi('/farms'));
  assert.ok(selection.nodeId,'Account must have an authorized node; never create memberships in a check');
  const checks=[];
  for(const farm of farms) for(const site of farm.sites) for(const node of site.nodes.filter(n=>['NODE_01','NODE_02'].includes(n.node_id))) {
    const loaded=await loadFarmWorkspace(accessApi,farm.farm_id,selectionQuery(site.site_id,node.node_id));
    assert.equal(loaded.history.request.observations.length,336);
    assert.equal(historicalSeries(loaded.history.request.observations).length,336);
    for(const model of MODELS) {
      const saved=await accessApi(`/farms/${farm.farm_id}/forecast`,{method:'POST',body:{site_id:site.site_id,node_id:node.node_id,model:model.id}});
      const result=validateForecast(saved.response,{...loaded.history.request,model:model.id});
      assert.ok(result.predictions.every(row=>FEATURES.every(key=>Number.isFinite(row[key]))));
      for(const horizon of [24,72,168]) assert.equal(groupForecastDays(result.predictions,horizon).reduce((n,d)=>n+d.count,0),horizon);
      checks.push({node:node.node_id,model:model.id,historical_hours:336,forecast_hours:168});
    }
  }
  assert.equal(new Set(checks.map(c=>c.node)).size,2);
  const denied=await sessionFetch(API_BASE+'/api/c2/access/users');assert.equal(denied.status,403);
  const yieldResult=await sessionFetch(API_BASE+'/api/c2/yield/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plant_height_cm:60,main_branches:5,leaf_length_cm:8,leaf_breadth_cm:3,days_to_50pct_flowering:45})});
  assert.equal(yieldResult.status,200);
  console.log(JSON.stringify({status:'passed',auto_selection:selection,checks,farmer_admin_denial:403,yield_status:200,browser_verified:false,evaluation_label:'Synthetic Data — Prototype Evaluation Only'},null,2));
} finally {
  if(cookie)await accessApi('/logout',{method:'POST'}).catch(()=>{});
  globalThis.fetch=originalFetch;
}
