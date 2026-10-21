import test from 'node:test';
import assert from 'node:assert/strict';
import { assignedFarmSelection, firstFarmSelection, loadFarmWorkspace } from '../../src/services/c2/farmSelection.js';

const farm = { farm_id:'sample', assigned:1, sites:[{site_id:'empty',nodes:[]},{site_id:'s1',nodes:[{node_id:'NODE_01'}]},{site_id:'s2',nodes:[{node_id:'NODE_02'}]}] };
test('selects first available authorized site/node rather than empty first site',()=> {
  assert.deepEqual(firstFarmSelection(farm),{farmId:'sample',siteId:'s1',nodeId:'NODE_01'});
  assert.equal(assignedFarmSelection([{farm_id:'empty',assigned:1,sites:[]},farm]).selection.nodeId,'NODE_01');
});
test('never selects unassigned farms or invents assignments',()=> {
  assert.equal(assignedFarmSelection([{...farm,assigned:0}]).selection.farmId,'');
  assert.deepEqual(assignedFarmSelection([]).farms,[]);
});
test('refresh preserves authorized selection and drops removed nodes',()=> {
  const previous={farmId:'sample',siteId:'s2',nodeId:'NODE_02'};
  assert.deepEqual(assignedFarmSelection([farm],previous).selection,previous);
  assert.equal(assignedFarmSelection([{...farm,sites:[]}],previous).selection.nodeId,'');
});
test('saved result failure does not prevent actual historical charts',async()=> {
  const history={request:{observations:[{timestamp:'2025-01-01T00:00:00Z'}]}};
  const result=await loadFarmWorkspace(async(path)=>{if(path.includes('/history?'))return history;throw new Error('Unavailable');},'sample','node_id=NODE_01');
  assert.equal(result.history,history);assert.deepEqual(result.saved,[]);assert.match(result.warning,/saved forecasts/);
});
test('history rejection cannot enable inference using invented data',async()=> {
  await assert.rejects(loadFarmWorkspace(async(path)=>{if(path.includes('/history?'))throw new Error('No source');return [];},'sample','node_id=NODE_01'),/No source/);
});
